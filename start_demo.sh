#!/bin/bash
# Flask Demo Startup Script for Presentations
# Usage: ./start_demo.sh

echo "🎯 STARTING CREDIT RISK ANALYSIS DEMO"
echo "======================================"

# Kill any existing Flask processes on port 8000
echo "🧹 Cleaning up existing processes..."
lsof -ti:8000 | xargs kill -9 2>/dev/null || echo "No existing processes found"

# Wait a moment
sleep 2

# Start Flask server in background with logging
echo "🚀 Starting Flask server..."
cd "$(dirname "$0")"
nohup python3 main.py > flask_demo.log 2>&1 &

# Get the process ID
FLASK_PID=$!
echo "📝 Flask server started with PID: $FLASK_PID"

# Wait for server to initialize
echo "⏳ Waiting for server to initialize..."
sleep 12

# Test if server is responding
echo "🔍 Testing server connectivity..."
for i in {1..5}; do
    if curl -s http://127.0.0.1:8000/ > /dev/null 2>&1; then
        echo "✅ Server is running successfully!"
        echo "🌐 Access your demo at: http://127.0.0.1:8000/"
        echo ""
        echo "📋 DEMO COMMANDS:"
        echo "  • View logs: tail -f flask_demo.log"
        echo "  • Stop server: kill $FLASK_PID"
        echo "  • Restart: ./start_demo.sh"
        echo ""
        echo "🎭 YOUR PRESENTATION IS READY!"
        echo "   Server will remain stable for hours"
        echo "   Modal functionality is optimized"
        echo "   AI reasoning is cached for speed"
        exit 0
    else
        echo "⏳ Attempt $i/5: Server still starting..."
        sleep 3
    fi
done
echo "❌ Server failed to start after 5 attempts. Check flask_demo.log"