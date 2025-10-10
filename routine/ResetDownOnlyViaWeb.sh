#!/bin/bash

echo "Starting Reset Down Port Only operation via web API..."
echo

# Set the domain and port using SERVER_PORT environment variable
DOMAIN="127.0.0.1"
ENDPOINT="/api/network/reset_down_port_only_sse"

# Use SERVER_PORT environment variable, default to 5000 if not set
if [ -z "$SERVER_PORT" ]; then
    SERVER_PORT=5000
fi

echo "Using port: $SERVER_PORT"

# Make the curl request to reset down ports only
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"timeout": 30}' \
  "http://$DOMAIN:$SERVER_PORT$ENDPOINT"

echo
echo "Operation completed."
read -p "Press Enter to continue..."
