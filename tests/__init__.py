import pytest
from web import app as flask_app

@pytest.fixture
def client():
    return flask_app.app.test_client()
