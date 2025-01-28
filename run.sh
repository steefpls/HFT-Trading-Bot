#!/bin/bash

# Function to start main.py and restart it if it crashes
run_main_py() {
    until python main.py; do
        echo "main.py crashed with exit code $?. Respawning.." >&2
        sleep 1
    done
}

echo "Checking for missing dependencies..."
check_and_install_dependencies
echo "Starting main.py..."
run_main_py
