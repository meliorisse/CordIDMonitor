#!/bin/bash
# Get the directory where this script resides (project root)
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# Path to venv python (assumes venv is in the project root)
VENV_PYTHON="$SCRIPT_DIR/venv/bin/python3"

# Add the 'src' directory to PYTHONPATH
export PYTHONPATH=$PYTHONPATH:$SCRIPT_DIR/src

# Check if venv exists and use it, otherwise fall back to system python
if [ -f "$VENV_PYTHON" ]; then
    echo "Launching with venv: $VENV_PYTHON"
    exec "$VENV_PYTHON" -m cord_id_monitor.main
else
    echo "Warning: venv not found at $VENV_PYTHON. Using system python3."
    exec python3 -m cord_id_monitor.main
fi