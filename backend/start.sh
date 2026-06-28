#!/bin/bash
# Start script for Family Assistant backend

echo "Starting Family Assistant Backend..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "Warning: .env file not found"
    echo "Creating default .env file..."

    cat > .env << EOF
# Database
DATABASE_URL=sqlite:///./family_assistant.db

# LLM Configuration
LLM_API_BASE=https://api.openai.com/v1
LLM_API_KEY=your_api_key_here
LLM_MODEL=gpt-3.5-turbo

# Feishu Configuration (optional)
FEISHU_APP_ID=
FEISHU_APP_SECRET=
FEISHU_MODE=webhook

# Session Configuration
SESSION_MAX_HISTORY=10

# Trigger Configuration
TRIGGER_ENABLED=true
EOF

    echo "Please update .env file with your actual configuration"
fi

# Start the backend server
echo ""
echo "Starting FastAPI server on http://localhost:8000"
echo ""
echo "Available endpoints:"
echo "  - GET  /                  : API info"
echo "  - POST /chat/web          : Web frontend chat (REST)"
echo "  - POST /chat/web/action   : Web frontend card actions"
echo "  - WS   /chat/ws/{user_id} : WebSocket real-time chat"
echo "  - GET  /chat/ws/health    : WebSocket health check"
echo ""
echo "Open backend/web_example.html to test the web frontend"
echo ""

uvicorn app.main:app --reload --port 8000