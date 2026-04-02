#!/bin/bash
# Server Health Monitor and Auto-Restart Script
# This script ensures the Flask server stays running

SERVER_PORT=5002
LOG_FILE="server_monitor.log"
PID_FILE="server.pid"

check_server() {
    if curl -s "http://localhost:${SERVER_PORT}/api/modular/health" > /dev/null 2>&1; then
        return 0  # Server is running
    else
        return 1  # Server is down
    fi
}

start_server() {
    echo "$(date): Starting Flask server..." >> "$LOG_FILE"
    cd /Users/kaunteyshah/Databricks/Credit_Risk/clean_modular_app
    nohup python3 stable_server.py > server_output.log 2>&1 &
    echo $! > "$PID_FILE"
    sleep 5
    if check_server; then
        echo "$(date): Server started successfully on port $SERVER_PORT" >> "$LOG_FILE"
        return 0
    else
        echo "$(date): Server failed to start" >> "$LOG_FILE"
        return 1
    fi
}

stop_server() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            kill "$PID"
            rm -f "$PID_FILE"
            echo "$(date): Server stopped (PID: $PID)" >> "$LOG_FILE"
        fi
    fi
    # Also kill any other Flask processes
    pkill -f "python.*stable_server" 2>/dev/null || true
}

restart_server() {
    echo "$(date): Restarting server..." >> "$LOG_FILE"
    stop_server
    sleep 2
    start_server
}

monitor_server() {
    while true; do
        if ! check_server; then
            echo "$(date): Server is down, restarting..." >> "$LOG_FILE"
            restart_server
        else
            echo "$(date): Server is healthy" >> "$LOG_FILE"
        fi
        sleep 30  # Check every 30 seconds
    done
}

case "$1" in
    start)
        start_server
        ;;
    stop)
        stop_server
        ;;
    restart)
        restart_server
        ;;
    monitor)
        monitor_server
        ;;
    status)
        if check_server; then
            echo "✅ Server is running and healthy"
        else
            echo "❌ Server is down or not responding"
        fi
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|monitor}"
        echo ""
        echo "Commands:"
        echo "  start   - Start the Flask server"
        echo "  stop    - Stop the Flask server"  
        echo "  restart - Restart the Flask server"
        echo "  status  - Check if server is running"
        echo "  monitor - Continuously monitor and restart if needed"
        exit 1
        ;;
esac