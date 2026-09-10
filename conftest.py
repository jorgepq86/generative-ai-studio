import sys
from pathlib import Path
from streamlit.testing.v1 import AppTest

# Add root to path so lib is importable from tests
sys.path.insert(0, str(Path(__file__).parent))

# Monkeypatch AppTest.from_file to resolve relative paths against project root
_original_from_file = AppTest.from_file

@classmethod
def _patched_from_file(cls, script_path, *, default_timeout=3):
    script_path = Path(script_path)
    if not script_path.is_absolute():
        # Resolve relative paths against project root, not caller's directory
        script_path = Path(__file__).parent / script_path
    return _original_from_file(str(script_path), default_timeout=default_timeout)

AppTest.from_file = _patched_from_file
