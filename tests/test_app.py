import os
import importlib
from web import app as flask_app


def test_login_required(client):
    resp = client.get('/dashboard', follow_redirects=False)
    assert resp.status_code == 302


def test_login_success(client, monkeypatch):
    monkeypatch.setenv('ADMIN_USER', 'adm')
    monkeypatch.setenv('ADMIN_PASS', 'pwd')
    importlib.reload(flask_app)
    with flask_app.app.test_client() as c:
        resp = c.post('/login', data={'username': 'adm', 'password': 'pwd'}, follow_redirects=True)
        assert b'Logged in successfully' in resp.data
