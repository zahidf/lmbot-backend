import sys
import pytest
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture(scope="session")
def client():
    """Single TestClient shared across the entire test session.

    The SQLAlchemy async engine (database.py) is a module-level singleton
    whose asyncpg connections are bound to the event loop they were created
    on.  Each TestClient context manager starts its own event loop; if more
    than one context is opened during a session, the second one tries to
    reuse pool connections from the first (now-closed) loop and crashes with
    'NoneType has no attribute send'.

    Using scope="session" means ONE context → ONE event loop → connections
    stay valid for every integration and e2e test in the run.
    """
    from fastapi.testclient import TestClient
    from main import app

    with TestClient(app) as c:
        yield c
