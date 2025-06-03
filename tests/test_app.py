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


def test_parse_send_log_multiple_days(tmp_path, monkeypatch):
    log = tmp_path / "send.log"
    log.write_text(
        """
--- Gönderim Başladı: 2023-10-01 10:00 ---
[OK] a@example.com
--- Gönderim Bitti: 2023-10-01 10:05 ---
--- Gönderim Başladı: 2023-10-02 11:00 ---
[OK] b@example.com
[OK] c@example.com
"""
    )
    monkeypatch.setattr(flask_app, "SEND_LOG", str(log))
    total, per_day = flask_app.parse_send_log()
    assert total == 3
    assert per_day == {"2023-10-01": 1, "2023-10-02": 2}


def test_parse_send_log_filter_range(tmp_path, monkeypatch):
    log = tmp_path / "send.log"
    old_date = (flask_app.datetime.now() - flask_app.timedelta(days=10)).strftime("%Y-%m-%d")
    today = flask_app.datetime.now().strftime("%Y-%m-%d")
    log.write_text(
        f"""
--- Gönderim Başladı: {old_date} 10:00 ---
[OK] old@example.com
--- Gönderim Bitti: {old_date} 10:01 ---
--- Gönderim Başladı: {today} 12:00 ---
[OK] new@example.com
"""
    )
    monkeypatch.setattr(flask_app, "SEND_LOG", str(log))
    total, per_day = flask_app.parse_send_log()
    start = (flask_app.datetime.now() - flask_app.timedelta(days=7)).strftime("%Y-%m-%d")
    per_day = {d: c for d, c in per_day.items() if d >= start}
    assert total == 2
    assert list(per_day.keys()) == [today]


def test_get_smtp_limits(tmp_path, monkeypatch):
    home = tmp_path
    (home / "input").mkdir()
    (home / "logs").mkdir()
    df = flask_app.pd.DataFrame({"Mail": ["a@example.com"], "Günlük Limit": [100]})
    df.to_excel(home / "input" / "Senders.xlsx", index=False)
    counters = {"a@example.com": 40}
    day = flask_app.datetime.now().strftime("%Y-%m-%d")
    counter_path = home / "logs" / "daily_counter.json"
    counter_path.write_text(flask_app.json.dumps({day: counters}))
    monkeypatch.setenv("CLEANMAILER_HOME", str(home))
    importlib.reload(flask_app)
    limits = flask_app.get_smtp_limits()
    assert limits == [
        {"email": "a@example.com", "used": 40, "limit": 100, "remaining": 60}
    ]
