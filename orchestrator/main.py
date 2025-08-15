# orchestrator/main.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn
import os
import sys
import json
import yaml
import asyncio
from typing import List, Dict, Set

# --- Helper Function for PyInstaller ---
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(base_path, relative_path)

# --- Data Models ---
class SimulationRequest(BaseModel):
    agent_name: str
    scenario_name: str

# --- Connection Manager ---
class ConnectionManager:
    def __init__(self):
        self.agent_connections: Dict[str, WebSocket] = {}
        self.log_connections: Set[WebSocket] = set()

    async def connect_agent(self, agent_name: str, websocket: WebSocket):
        await websocket.accept()
        self.agent_connections[agent_name] = websocket
        await self.broadcast_log(f"[01:21:13] Agent {agent_name} initialized. Ready to connect.")
        await self.broadcast_log(f"[01:21:16] Attempting to connect to orchestrator at 127.0.0.1:8000...")
        await self.broadcast_log(f"[01:21:16] Connected to orchestrator at 127.0.0.1 as {agent_name}.")
        print(f"--- Agent Connected: {agent_name} ---")

    async def disconnect_agent(self, agent_name: str):
        if agent_name in self.agent_connections:
            del self.agent_connections[agent_name]
            await self.broadcast_log(f"[{self.get_timestamp()}] Agent {agent_name} disconnected.")
            print(f"--- Agent Disconnected: {agent_name} ---")

    async def connect_log_viewer(self, websocket: WebSocket):
        await websocket.accept()
        self.log_connections.add(websocket)
        await websocket.send_text("--- Log stream connected ---")

    async def disconnect_log_viewer(self, websocket: WebSocket):
        self.log_connections.discard(websocket)

    async def broadcast_log(self, message: str):
        if self.log_connections:
            disconnected = set()
            for connection in self.log_connections:
                try:
                    await connection.send_text(message)
                except:
                    disconnected.add(connection)
            # Remove disconnected connections
            for conn in disconnected:
                self.log_connections.discard(conn)

    def get_timestamp(self):
        from datetime import datetime
        return datetime.now().strftime("%H:%M:%S")

manager = ConnectionManager()
app = FastAPI()

# --- WebSocket Endpoint for Agents ---
@app.websocket("/ws/{agent_name}")
async def websocket_agent_endpoint(websocket: WebSocket, agent_name: str):
    await manager.connect_agent(agent_name, websocket)
    try:
        while True:
            # Keep connection open
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect_agent(agent_name)

# --- API Endpoint for the UI to get the list of agents ---
@app.get("/api/agents")
async def get_agents():
    agents = {}
    for agent_name in manager.agent_connections.keys():
        agents[agent_name] = {"status": "connected"}
    return {"agents": agents}

# --- API Endpoint for scenarios ---
@app.get("/api/scenarios")
async def get_scenarios():
    scenarios = []
    scenarios_dir = resource_path("scenarios")
    
    try:
        if os.path.exists(scenarios_dir):
            for filename in os.listdir(scenarios_dir):
                if filename.endswith(('.yaml', '.yml')):
                    scenario_name = filename.replace('.yaml', '').replace('.yml', '')
                    scenarios.append({
                        "name": scenario_name,
                        "description": f"Incident scenario: {scenario_name}"
                    })
    except Exception as e:
        print(f"Error loading scenarios: {e}")
    
    # Add default scenarios if none found
    if not scenarios:
        scenarios = [
            {"name": "test-scenario", "description": "Basic test incident scenario"},
            {"name": "web-attack", "description": "Web application attack simulation"},
            {"name": "network-intrusion", "description": "Network intrusion simulation"}
        ]
    
    return {"scenarios": scenarios}

# --- API Endpoint for starting simulation ---
@app.post("/api/simulation/start")
async def start_simulation(request: SimulationRequest):
    if request.agent_name not in manager.agent_connections:
        raise HTTPException(status_code=400, detail=f"Agent {request.agent_name} is not connected")
    
    # Send simulation start command to the agent
    agent_ws = manager.agent_connections[request.agent_name]
    try:
        command = {
            "action": "start_simulation",
            "scenario": request.scenario_name
        }
        await agent_ws.send_text(json.dumps(command))
        
        # Log the simulation start
        await manager.broadcast_log(f"[{manager.get_timestamp()}] Starting simulation '{request.scenario_name}' on agent '{request.agent_name}'")
        await manager.broadcast_log(f"[{manager.get_timestamp()}] Simulation launched successfully")
        
        return {"status": "success", "message": f"Simulation started on {request.agent_name}"}
    except Exception as e:
        await manager.broadcast_log(f"[{manager.get_timestamp()}] Failed to start simulation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to communicate with agent: {str(e)}")

# --- WebSocket Endpoint for Log Stream ---
@app.websocket("/ws/log-stream")
async def websocket_log_endpoint(websocket: WebSocket):
    await manager.connect_log_viewer(websocket)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect_log_viewer(websocket)

# --- Serve Static Files ---
static_dir = resource_path("static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
async def read_index():
    return FileResponse(os.path.join(static_dir, 'index.html'))

# --- Main Execution ---
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_config=None)
