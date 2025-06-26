import pytest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from web import app as flask_app
import werkzeug
if not hasattr(werkzeug, "__version__"):
    werkzeug.__version__ = "3"

@pytest.fixture
def client():
    return flask_app.app.test_client()
