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
import sys # New import
import json  # Add json import
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
        self.agent_connections: dict[str, WebSocket] = {}  # Map agent names to their WebSocket connections
        
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        
    async def connect_agent(self, agent_name: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        self.agent_connections[agent_name] = websocket
        
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            
    def disconnect_agent(self, agent_name: str):
        if agent_name in self.agent_connections:
            websocket = self.agent_connections[agent_name]
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
            del self.agent_connections[agent_name]
            
    async def broadcast(self, message: str):
        # Create a copy of the connections list to avoid modification during iteration
        connections_copy = self.active_connections.copy()
        for connection in connections_copy:
            try:
                await connection.send_text(message)
            except Exception as e:
                print(f"--- Error sending message to WebSocket client: {e} ---")
                # Remove the failed connection
                self.disconnect(connection)
                
    async def send_to_agent(self, agent_name: str, message: str):
        if agent_name in self.agent_connections:
            try:
                await self.agent_connections[agent_name].send_text(message)
                return True
            except Exception as e:
                print(f"--- Error sending message to agent {agent_name}: {e} ---")
                self.disconnect_agent(agent_name)
                return False
        return False

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

# --- Helper Functions ---
def load_scenarios():
    # FIX: Use resource_path to find the scenarios directory
    scenarios_dir = resource_path("scenarios")
    if not os.path.exists(scenarios_dir):
        print(f"--- WARNING: Scenarios directory '{scenarios_dir}' not found. ---")
        return
    for filename in os.listdir(scenarios_dir):
        if filename.endswith((".yaml", ".yml")):
            filepath = os.path.join(scenarios_dir, filename)
            db["scenarios"].append({"name": filename, "compose_file_path": filepath})
    print(f"--- Loaded {len(db['scenarios'])} scenarios. ---")

# Create the FastAPI application instance
app = FastAPI(
    title="LISE Orchestrator API",
    description="The central command server for the Local Incident Simulation Environment.",
    version="1.0.0"
)

# --- Mount Static Files ---
# FIX: Use the resource_path helper to find the static directory
app.mount("/static", StaticFiles(directory=resource_path("static")), name="static")

# --- IN-MEMORY DATABASE ---
db = { "agents": {}, "scenarios": [] }

# --- API ENDPOINTS ---

@app.get("/", response_class=FileResponse, tags=["UI"])
async def read_index():
    # FIX: Use resource_path to find the index.html file
    return resource_path("static/index.html")

@app.websocket("/ws/log-stream")
async def websocket_log_endpoint(websocket: WebSocket):
    try:
        await manager.connect(websocket)
        print("--- UI Client connected to logs ---")
        while True:
            # Keep connection alive by receiving messages
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print("--- UI Client disconnected from logs ---")
    except Exception as e:
        print(f"--- WebSocket error: {e} ---")
        if websocket in manager.active_connections:
            manager.disconnect(websocket)

@app.websocket("/ws/{agent_name}")
async def websocket_agent_endpoint(websocket: WebSocket, agent_name: str):
    try:
        await manager.connect_agent(agent_name, websocket)
        print(f"--- Agent {agent_name} connected to orchestrator ---")
        
        # Register the agent automatically when they connect
        # You can enhance this to get the actual IP from the websocket
        agent_ip = websocket.client.host if websocket.client else "unknown"
        db["agents"][agent_name] = {"ip_address": agent_ip, "websocket": True}
        print(f"--- Agent Registered: {agent_name} at {agent_ip} ---")
        
        while True:
            # Keep connection alive and handle any messages from agent
            try:
                message = await websocket.receive_text()
                print(f"--- Received from {agent_name}: {message} ---")
                # Echo back or handle the message as needed
                await websocket.send_text(f"Orchestrator received: {message}")
            except Exception as e:
                print(f"--- Error receiving message from {agent_name}: {e} ---")
                break
                
    except WebSocketDisconnect:
        manager.disconnect_agent(agent_name)
        print(f"--- Agent {agent_name} disconnected from orchestrator ---")
        # Remove agent from registered agents
        if agent_name in db["agents"]:
            del db["agents"][agent_name]
            print(f"--- Agent {agent_name} unregistered ---")
    except Exception as e:
        print(f"--- WebSocket error with {agent_name}: {e} ---")
        manager.disconnect_agent(agent_name)

@app.post("/api/log", tags=["Logging"])
async def receive_log(entry: LogEntry):
    log_message = f"[{entry.agent_name}] {entry.log_line}"
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

    # Try to send command via WebSocket first (preferred method)
    if agent_info.get("websocket"):
        command = {
            "action": "start_simulation",
            "scenario_id": sim_request.scenario_name,
            "scenario_path": scenario_info["compose_file_path"]
        }
        
        success = await manager.send_to_agent(sim_request.agent_name, json.dumps(command))
        if success:
            print(f"--- Sent start command via WebSocket for '{sim_request.scenario_name}' to {sim_request.agent_name} ---")
            return {"status": "success", "message": f"Simulation start command sent to {sim_request.agent_name}"}
        else:
            # WebSocket failed, fall back to HTTP
            print(f"--- WebSocket failed for {sim_request.agent_name}, falling back to HTTP ---")
    
    # Fallback to HTTP method
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

# This block allows us to run the server directly from the script
if __name__ == "__main__":
    print("--- Starting LISE Orchestrator Server ---")
    # Load scenarios at startup
    load_scenarios()
    print("--- Starting uvicorn server ---")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_config=None)
