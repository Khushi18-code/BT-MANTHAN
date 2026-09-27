"""WSGI entry point for Railway.

Railway builds from the repository root; Server.py lives in backend/.
This shim puts backend/ on the import path and exposes the Flask app
at root level without touching the backend's own imports.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "backend"))

from Server import app  # noqa: E402

if __name__ == "__main__":
    app.run()
