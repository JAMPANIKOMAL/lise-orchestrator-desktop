# Dockerfile.red: Defines a basic attacker environment for the Red Team.

# Start from a minimal base image
FROM alpine:latest

# Install the 'curl' utility for making HTTP requests.
# --no-cache prevents storing the package index, keeping the image small.
RUN apk add --no-cache curl

# This command keeps the container running indefinitely,
# allowing the Red Team user to get a shell inside it using 'docker exec'.
CMD ["tail", "-f", "/dev/null"]
