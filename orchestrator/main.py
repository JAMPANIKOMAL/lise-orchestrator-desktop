# orchestrator/main.py
# The main application for the LISE Orchestrator.

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn
import yaml
import os
import requests
import sys
from typing import List, Dict, Any, Optional

# --- Helper Function for PyInstaller ---
def resource_path(relative_path: str) -> str:
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# --- Connection Manager for WebSockets ---
class ConnectionManager:
    """Manages active WebSocket connections for real-time log streaming."""
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        """Sends a message to all connected clients."""
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

# --- Pydantic Models ---
class AgentRegistration(BaseModel):
    display_name: str
    ip_address: str

class SimulationRequest(BaseModel):
    agent_name: str
    scenario_name: str

class LogEntry(BaseModel):
    agent_name: str
    log_line: str

# Create the FastAPI application instance
app = FastAPI(
    title="LISE Orchestrator API",
    description="The central command server for the Local Incident Simulation Environment.",
    version="1.0.0"
)

# --- Mount Static Files ---
app.mount("/static", StaticFiles(directory=resource_path("static")), name="static")

# --- IN-MEMORY DATABASE ---
db = {"agents": {}, "scenarios": []}

# --- Helper Functions ---
def load_scenarios():
    """Loads scenario definitions from YAML files in the scenarios directory."""
    scenarios_dir = resource_path("scenarios")
    if not os.path.exists(scenarios_dir):
        print(f"--- WARNING: Scenarios directory '{scenarios_dir}' not found. ---")
        return
    for filename in os.listdir(scenarios_dir):
        if filename.endswith((".yaml", ".yml")):
            filepath = os.path.join(scenarios_dir, filename)
            db["scenarios"].append({"name": filename, "compose_file_path": filepath})
    print(f"--- Loaded {len(db['scenarios'])} scenarios. ---")

# --- FastAPI Events ---
@app.on_event("startup")
async def startup_event():
    load_scenarios()

# --- API ENDPOINTS ---
@app.get("/", response_class=FileResponse, tags=["UI"])
async def read_index():
    """Serves the main static HTML file for the orchestrator UI."""
    return resource_path("static/index.html")

@app.websocket("/ws/log-stream")
async def websocket_endpoint(websocket: WebSocket):
    """Establishes a WebSocket connection for log streaming."""
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print("--- UI Client disconnected from logs ---")

@app.post("/api/log", tags=["Logging"])
async def receive_log(entry: LogEntry):
    """Receives a log entry from an agent and broadcasts it to UI clients."""
    log_message = f"[{entry.agent_name}] {entry.log_line}"
    await manager.broadcast(log_message)
    return {"status": "log received"}

@app.post("/api/agents/register", tags=["Agent Management"])
async def register_agent(agent: AgentRegistration):
    """Registers an agent with the orchestrator."""
    db["agents"][agent.display_name] = {"ip_address": agent.ip_address}
    print(f"--- Agent Registered: {agent.display_name} at {agent.ip_address} ---")
    return {"status": "success", "message": f"Agent '{agent.display_name}' registered."}

@app.get("/api/agents", tags=["Agent Management"])
async def get_registered_agents():
    """Returns the list of currently registered agents."""
    return {"agents": db["agents"]}

@app.get("/api/scenarios", tags=["Scenario Management"])
async def get_scenarios():
    """Returns the list of available scenarios."""
    return {"scenarios": db["scenarios"]}

@app.post("/api/simulation/start", tags=["Simulation Control"])
async def start_simulation(sim_request: SimulationRequest):
    """Sends a command to an agent to start a specific simulation."""
    agent_info = db["agents"].get(sim_request.agent_name)
    if not agent_info:
        raise HTTPException(status_code=404, detail=f"Agent '{sim_request.agent_name}' not found.")

    scenario_info = next((s for s in db["scenarios"] if s["name"] == sim_request.scenario_name), None)
    if not scenario_info:
        raise HTTPException(status_code=404, detail=f"Scenario '{sim_request.scenario_name}' not found.")

    agent_ip = agent_info["ip_address"]
    agent_url = f"http://{agent_ip}:8000/api/scenario/start"
    payload = {"compose_file_path": scenario_info["compose_file_path"]}

    try:
        print(f"--- Sending start command for '{sim_request.scenario_name}' to {sim_request.agent_name} at {agent_ip} ---")
        response = requests.post(agent_url, json=payload, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Failed to send command to agent: {e}")

@app.post("/api/simulation/stop", tags=["Simulation Control"])
async def stop_simulation(agent_name: str):
    """Sends a command to an agent to stop the running simulation."""
    agent_info = db["agents"].get(agent_name)
    if not agent_info:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found.")
    
    agent_ip = agent_info["ip_address"]
    agent_url = f"http://{agent_ip}:8000/api/scenario/stop"

    try:
        print(f"--- Sending stop command to {agent_name} at {agent_ip} ---")
        response = requests.post(agent_url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Failed to send stop command to agent: {e}")


# This block allows us to run the server directly from the script
if __name__ == "__main__":
    print("--- Starting LISE Orchestrator Server ---")
    uvicorn.run(app, host="0.0.0.0", port=8080)
