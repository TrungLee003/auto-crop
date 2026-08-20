import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Add project root to sys.path
root_path = Path(__file__).resolve().parent.parent.parent
if str(root_path) not in sys.path:
    sys.path.insert(0, str(root_path))

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)
