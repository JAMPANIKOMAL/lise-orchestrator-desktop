#!/bin/bash

# A robust startup script for the LISE "VM" container.
# This script launches the necessary services for the simulation.

# Log startup message
echo "--- Starting LISE Virtual Machine Environment ---"

# Start the VNC server first on display :1 (port 5901)
# The `vncserver` command is from the TigerVNC package.
# We set a password and chmod it for security, but for this demo,
# we'll run without a password for simplicity.
# The `-geometry` sets the screen resolution.
echo "Starting VNC server on display :1..."
vncserver :1 -geometry 1280x720 -depth 24 -rfbport 5901 -SecurityTypes None &

# Wait a moment for the VNC server to initialize
sleep 2

# Launch the QEMU VM and connect its display to the VNC server.
# The `-vnc` flag tells QEMU to use a VNC display.
# The `localhost:1` refers to the VNC server we started above.
# The `-daemonize` flag is crucial; it detaches QEMU from the terminal,
# allowing the script to continue and not exit prematurely.
echo "Starting QEMU VM..."
qemu-system-i386 -m 512 -cdrom /app/tinycore.iso -vnc localhost:1 -daemonize

# Start the vulnerable web application in the background.
echo "Starting vulnerable_app.py..."
python3 /app/vulnerable_app.py &

# Keep the container running indefinitely by running a long-lived process.
# Without this, the container would exit as soon as this script finishes.
echo "Startup complete. Keeping container alive."
tail -f /dev/null
