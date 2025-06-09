import importlib.util
from pathlib import Path
import pandas as pd

class DummySMTP:
    sent = []
    def __init__(self, host, port):
        self.host = host
        self.port = port
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        pass
    def login(self, user, password):
        self.user = user
        self.password = password
    def sendmail(self, from_addr, to_addr, msg):
        DummySMTP.sent.append(from_addr)


def load_module(monkeypatch, home):
    monkeypatch.setenv('CLEANMAILER_HOME', str(home))
    module_path = Path(__file__).resolve().parents[1] / 'scripts' / '03_send_mails.py'
    spec = importlib.util.spec_from_file_location('send_mails', module_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def setup_files(tmp_path):
    input_dir = tmp_path / 'input'
    reports_dir = tmp_path / 'reports'
    templates_dir = tmp_path / 'templates'
    logs_dir = tmp_path / 'logs'
    input_dir.mkdir()
    reports_dir.mkdir()
    templates_dir.mkdir()
    logs_dir.mkdir()

    df_senders = pd.DataFrame({
        'Mail': ['a@example.com', 'b@example.com'],
        'Mdp': ['pa', 'pb'],
        'SMTP Host': ['smtp.a', 'smtp.b'],
        'SMTP Port': [465, 465],
        'Nom': ['A', 'B'],
        'Günlük Limit': [10, 10],
    })
    df_senders.to_excel(input_dir / 'Senders.xlsx', index=False)

    df_targets = pd.DataFrame({'email': ['x@example.com', 'y@example.com', 'z@example.com']})
    df_targets.to_excel(reports_dir / 'aktif_mailler.xlsx', index=False)

    (templates_dir / 'mail_template.txt').write_text('hello')

    (logs_dir / 'daily_counter.json').write_text('{}')


def test_one_per_account(monkeypatch, tmp_path):
    setup_files(tmp_path)
    mod = load_module(monkeypatch, tmp_path)
    monkeypatch.setattr(mod.smtplib, 'SMTP_SSL', DummySMTP)
    DummySMTP.sent = []
    mod.main()
    assert DummySMTP.sent == ['a@example.com', 'b@example.com']

