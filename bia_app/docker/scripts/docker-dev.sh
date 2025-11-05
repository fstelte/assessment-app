#!/bin/bash
# Development Docker helper script

cd "$(dirname "$0")/../docker"

case "$1" in
    "start")
        echo "Starting BIA Tool in development mode..."
        docker-compose up --build
        ;;
    "start-bg")
        echo "Starting BIA Tool in development mode (background)..."
        docker-compose up -d --build
        ;;
    "stop")
        echo "Stopping BIA"
