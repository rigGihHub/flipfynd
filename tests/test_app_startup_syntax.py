"""Check the real Streamlit entrypoint without network calls or app startup.

Text-based UI assertions do not detect syntax errors introduced during release
serialization. Compile the complete source, not an extracted helper function.
"""
from pathlib import Path


def test_streamlit_entrypoint_compiles():
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    compile(app_path.read_text(encoding="utf-8"), str(app_path), "exec")
