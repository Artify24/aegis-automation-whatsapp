#!/usr/bin/env bash
# AegisBot -- 1-Command Linux/macOS/Cloud Runner

set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "====================================================================="
echo "   AegisBot -- AI WhatsApp Business Operating System & Lead Engine   "
echo "====================================================================="
echo ""

# 1. Check for .env file
if [ ! -f "$DIR/.env" ]; then
    echo "[!] .env file not found. Creating from .env.example..."
    cp "$DIR/.env.example" "$DIR/.env"
    echo "[*] Created .env template. Please populate your API keys."
fi

# 2. Detect Python 3
if command -v python3 &>/dev/null; then
    PYTHON=python3
elif command -v python &>/dev/null; then
    PYTHON=python
else
    echo "[ERROR] Python 3 not found. Please install Python 3.10+."
    exit 1
fi

echo "[*] Using Python: $($PYTHON --version)"

# 3. Check / setup virtual environment (optional but recommended)
if [ -d "$DIR/.venv" ]; then
    echo "[*] Activating virtual environment (.venv)..."
    source "$DIR/.venv/bin/activate"
    PYTHON=python
fi

# 4. Check dependencies
echo "[*] Verifying dependencies..."
$PYTHON -c "import fastapi, uvicorn, supabase, groq, reportlab" 2>/dev/null || {
    echo "[*] Installing dependencies from requirements.txt..."
    $PYTHON -m pip install -r "$DIR/requirements.txt"
}

echo "[OK] Dependencies ready."
echo ""
echo "====================================================================="
echo "   Starting AegisBot Server on http://0.0.0.0:8000"
echo "   Web Dashboard:   http://localhost:8000"
echo "   Health Endpoint: http://localhost:8000/health"
echo "   Press Ctrl+C to terminate"
echo "====================================================================="
echo ""

exec $PYTHON -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
