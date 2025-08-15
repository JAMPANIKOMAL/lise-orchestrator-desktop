// --- DOM ELEMENTS ---
const agentListDiv = document.getElementById('agent-list');
const noAgentsMsg = document.getElementById('no-agents-msg');
const logViewer = document.getElementById('log-viewer');

// --- APPLICATION STATE ---
let state = {
    agents: []
};

// --- RENDER FUNCTIONS ---
function renderAgents() {
    agentListDiv.innerHTML = ''; // Clear current list
    if (state.agents.length === 0) {
        agentListDiv.appendChild(noAgentsMsg);
        noAgentsMsg.style.display = 'block';
    } else {
        noAgentsMsg.style.display = 'none';
        state.agents.forEach(name => {
            const div = document.createElement('div');
            div.className = 'agent-box p-4 border-2 rounded-lg text-center bg-white shadow text-gray-800';
            div.textContent = name;
            div.dataset.agentName = name;
            agentListDiv.appendChild(div);
        });
    }
}

function addLog(message) {
    const logLine = document.createElement('div');
    const timestamp = new Date().toLocaleTimeString();
    logLine.textContent = `[${timestamp}] ${message}`;
    logViewer.appendChild(logLine);
    logViewer.scrollTop = logViewer.scrollHeight;
}

// --- API FUNCTIONS ---
async function fetchAgents() {
    try {
        const response = await fetch('http://127.0.0.1:8000/api/agents');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        // Check if the list of agents has changed before re-rendering
        if (JSON.stringify(state.agents) !== JSON.stringify(data.agents)) {
            state.agents = data.agents;
            renderAgents();
            addLog(`Agent list updated: ${state.agents.join(', ') || 'No agents connected'}`);
        }
    } catch (error) {
        // Don't log periodic fetch errors to keep the UI clean
        console.error("Failed to fetch agents:", error);
    }
}

// --- INITIALIZATION ---
document.addEventListener('DOMContentLoaded', () => {
    addLog("Orchestrator UI Initialized. Waiting for agents...");
    renderAgents(); // Initial render
    // Fetch the agent list every 3 seconds
    setInterval(fetchAgents, 3000);
});
