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

# Start QEMU with monitor interface using Unix socket for better compatibility
qemu-system-i386 \
  -m 512 \
  -cdrom /app/tinycore.iso \
  -vnc 0.0.0.0:1 \
  -nographic \
  -boot d \
  -monitor unix:/tmp/qemu-monitor,server,nowait &

QEMU_PID=$!

# Wait for QEMU to start and reach the boot prompt
sleep 15

# Send Enter key via QEMU monitor using netcat or echo
echo "Sending Enter key to proceed with boot..."
echo "sendkey ret" | socat - unix:/tmp/qemu-monitor 2>/dev/null || true

# Wait for the QEMU process to complete
wait $QEMU_PID