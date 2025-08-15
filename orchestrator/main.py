# orchestrator/main.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn
import os
import sys
import json
from typing import List, Dict

# --- Helper Function for PyInstaller ---
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(base_path, relative_path)

# --- Connection Manager ---
class ConnectionManager:
    def __init__(self):
        self.agent_connections: Dict[str, WebSocket] = {}

    async def connect_agent(self, agent_name: str, websocket: WebSocket):
        await websocket.accept()
        self.agent_connections[agent_name] = websocket
        print(f"--- Agent Connected: {agent_name} ---")

    async def disconnect_agent(self, agent_name: str):
        if agent_name in self.agent_connections:
            del self.agent_connections[agent_name]
            print(f"--- Agent Disconnected: {agent_name} ---")

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
    return {"agents": list(manager.agent_connections.keys())}

# --- Serve Static Files ---
static_dir = resource_path("static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
async def read_index():
    return FileResponse(os.path.join(static_dir, 'index.html'))

# --- Main Execution ---
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_config=None)
