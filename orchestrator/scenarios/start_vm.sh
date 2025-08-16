#!/bin/bash

# A robust startup script for the LISE "VM" container.
# This script runs the VM as the main process to ensure the container stays alive.

# Log startup message
echo "--- Starting LISE Virtual Machine Environment ---"

# Start the vulnerable web application in the background.
echo "Starting vulnerable_app.py..."
python3 /app/vulnerable_app.py &

# --- 2. Start QEMU and connect it to the VNC server ---
# We run QEMU directly in the foreground, which is a more stable approach for Docker.
# The -vnc :1 option starts an internal VNC server on display :1 (port 5901)
# We also use -nographic to prevent QEMU from opening its own window.
# The exec command replaces the current shell with the QEMU process, ensuring it is the main process.
echo "Starting QEMU VM..."
exec qemu-system-i386 -m 512 -cdrom /app/tinycore.iso -vnc 0.0.0.0:1 -nographic