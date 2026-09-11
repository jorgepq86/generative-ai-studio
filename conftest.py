import sys
from pathlib import Path
from streamlit.testing.v1 import AppTest

sys.path.insert(0, str(Path(__file__).parent))

_original_from_file = AppTest.from_file

@classmethod
def _patched_from_file(cls, script_path, **kwargs):
    script_path = Path(script_path)
    if not script_path.is_absolute():
        script_path = Path(__file__).parent / script_path
    return _original_from_file(str(script_path), **kwargs)

AppTest.from_file = _patched_from_file
