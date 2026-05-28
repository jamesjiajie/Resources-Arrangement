#!/bin/zsh

set -e

PROJECT_DIR="/Users/james/Document/Projects/Resources-Arrangement"

cd "$PROJECT_DIR"

echo "Starting Resources Arrangement..."
echo "Project: $PROJECT_DIR"
echo

if [ ! -d "node_modules" ]; then
  echo "Installing frontend dependencies..."
  npm install
fi

if [ ! -x ".venv/bin/python" ]; then
  echo "Python virtual environment is missing or broken."
  echo "Please run setup first:"
  echo "  python3 -m venv .venv"
  echo "  .venv/bin/python -m pip install -r requirements.txt"
  echo
  read "reply?Press Enter to close..."
  exit 1
fi

echo "Opening http://127.0.0.1:8000/ after the server starts..."
(sleep 3 && open "http://127.0.0.1:8000/" >/dev/null 2>&1) &
echo

npm run dev

echo
read "reply?Server stopped. Press Enter to close..."
