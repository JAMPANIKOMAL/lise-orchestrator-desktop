# orchestrator/main.py
# The main application for the LISE Orchestrator.

from fastapi import FastAPI, Request, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn
import yaml
import os
import requests
import sys
import re
from typing import List

# --- Helper Function for PyInstaller ---
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# --- Connection Manager for WebSockets ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    async def broadcast(self, message: str):
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
    version="2.0.0"
)

# --- Mount Static Files ---
app.mount("/static", StaticFiles(directory=resource_path("static")), name="static")

# --- IN-MEMORY DATABASE ---
db = { "agents": {}, "scenarios": [] }

# --- Helper Functions ---
def load_scenarios():
    scenarios_dir = resource_path("scenarios")
    if not os.path.exists(scenarios_dir):
        print(f"--- WARNING: Scenarios directory '{scenarios_dir}' not found. ---")
        return
    for filename in os.listdir(scenarios_dir):
        if filename.endswith((".yaml", ".yml")):
            filepath = os.path.join(scenarios_dir, filename)
            db["scenarios"].append({"name": filename, "compose_file_path": filepath})
    print(f"--- Loaded {len(db['scenarios'])} scenarios. ---")

def strip_ansi_codes(s):
    """Removes ANSI escape codes from a string."""
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', s)

# --- FastAPI Events ---
@app.on_event("startup")
async def startup_event():
    load_scenarios()

# --- API ENDPOINTS ---

@app.get("/", response_class=FileResponse, tags=["UI"])
async def read_index():
    return resource_path("static/index.html")

@app.websocket("/ws/log-stream")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print("--- UI Client disconnected from logs ---")

@app.post("/api/log", tags=["Logging"])
async def receive_log(entry: LogEntry):
    log_line_clean = strip_ansi_codes(entry.log_line)
    log_message = f"[{entry.agent_name}] {log_line_clean}"
    await manager.broadcast(log_message)
    return {"status": "log received"}

@app.post("/api/agents/register", tags=["Agent Management"])
async def register_agent(agent: AgentRegistration):
    db["agents"][agent.display_name] = {"ip_address": agent.ip_address}
    print(f"--- Agent Registered: {agent.display_name} at {agent.ip_address} ---")
    return {"status": "success", "message": f"Agent '{agent.display_name}' registered."}

@app.get("/api/agents", tags=["Agent Management"])
async def get_registered_agents():
    return {"agents": db["agents"]}

@app.get("/api/scenarios", tags=["Scenario Management"])
async def get_scenarios():
    return {"scenarios": db["scenarios"]}

@app.post("/api/simulation/start", tags=["Simulation Control"])
async def start_simulation(sim_request: SimulationRequest):
    agent_info = db["agents"].get(sim_request.agent_name)
    if not agent_info:
        raise HTTPException(status_code=404, detail=f"Agent '{sim_request.agent_name}' not found.")

    scenario_info = next((s for s in db["scenarios"] if s["name"] == sim_request.scenario_name), None)
    if not scenario_info:
        raise HTTPException(status_code=404, detail=f"Scenario '{sim_request.scenario_name}' not found.")

    agent_ip = agent_info["ip_address"]
    agent_url = f"http://{agent_ip}:8000/api/scenario/start"

    scenario_file_path = scenario_info["compose_file_path"]
    try:
        with open(scenario_file_path, 'r') as f:
            scenario_content = f.read()

        payload = {
            "compose_file_content": scenario_content,
            "vnc_port": 5901,
            "web_port": 5000
        }
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Scenario file not found: {scenario_file_path}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading scenario file: {e}")

    try:
        print(f"--- Sending start command for '{sim_request.scenario_name}' to {sim_request.agent_name} at {agent_ip} ---")
        response = requests.post(agent_url, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Failed to send command to agent: {e}")

# This block allows us to run the server directly from the script
if __name__ == "__main__":
    print("--- Starting LISE Orchestrator Server ---")
    uvicorn.run(app, host="0.0.0.0", port=8080)