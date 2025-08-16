# Use a lightweight Debian base image
FROM debian:bullseye-slim

# Set environment variables to prevent interactive prompts during installation
ENV DEBIAN_FRONTEND=noninteractive

# Install necessary packages:
# - qemu-system-x86: The emulator to run the VM
# - wget: To download the VM image
# - tigervnc-standalone-server: The VNC server
# - net-tools: For basic network utilities inside the container
RUN apt-get update && \
    apt-get install -y \
    qemu-system-x86 \
    wget \
    tigervnc-standalone-server \
    net-tools \
    python3 \
    python3-flask \
    && \
    rm -rf /var/lib/apt/lists/*

# Download and prepare the Tiny Core Linux image for our proof-of-concept
WORKDIR /app
RUN wget http://tinycorelinux.net/13.x/x86/release/Core-current.iso -O tinycore.iso

# Copy the vulnerable Flask application and the startup script
# These paths are now relative to the current directory
COPY vulnerable_app.py /app/vulnerable_app.py
COPY start_vm.sh /start_vm.sh
RUN chmod +x /start_vm.sh

# Expose the VNC port (5901) and web server port (5000)
EXPOSE 5901 5000

# The command to run when the container starts:
CMD ["/start_vm.sh"]