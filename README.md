# LISE Orchestrator (Desktop Application)

LISE Orchestrator is the instructor-facing component of the Local Incident Simulation Environment (LISE). It is a native desktop application that acts as the central hub for creating, managing, and monitoring live cybersecurity exercises.

## Technology Stack

- **Application Framework:** Tauri (v2)
- **Frontend:** HTML, Tailwind CSS, Vanilla JavaScript
- **Backend:** Python (FastAPI)
- **Communication:** WebSockets
- **Installer:** MSI via Tauri

## Features

- **Agent Management:** View a real-time list of connected LISE Agents.
- **Scenario Control:** Select from a library of pre-defined incident scenarios.
- **Team Assignment:** Assign agents to Red or Blue teams using drag-and-drop or click.
- **Simulation Lifecycle:** Start/stop simulations for all agents with one click.
- **Real-time Communication:** Instantly send commands to agents via WebSockets.

## Setup and Development

Follow these steps to set up a local development environment.

### Prerequisites

- [Rust](https://www.rust-lang.org/tools/install)
- [Node.js (LTS)](https://nodejs.org/)
- [Python (3.8+)](https://www.python.org/downloads/)

### 1. Clone the Repository

```sh
git clone <your-repository-url>
cd lise-orchestrator-desktop
```

### 2. Install Frontend Dependencies

```sh
npm install
```

### 3. Set Up Python Environment

Create a virtual environment and install required packages:

```sh
cd orchestrator
python -m venv venv
.\venv\Scripts\activate  # On Windows
pip install -r requirements.txt
```

### 4. Build the Python Backend Executable

Compile the backend into a standalone `.exe` using PyInstaller:

```sh
cd ..
pyinstaller --noconsole --onefile --add-data "orchestrator/static;static" orchestrator/main.py
```

### 5. Position the Backend Executable

After building, copy `main.exe` from the `dist` folder into the `src-tauri` folder.

### 6. Run the Application

Start the application in development mode:

```sh
npm run tauri dev
```

## Building for Production

To create an MSI installer:

```sh
npm run tauri build
```

The installer will be located in `src-tauri/target/release/bundle/msi/`.
