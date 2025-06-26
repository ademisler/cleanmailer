import importlib.util
from pathlib import Path
import pandas as pd

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "01_filter_existing.py"

def load_module():
    spec = importlib.util.spec_from_file_location("filter_mod", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_filter_existing(tmp_path, monkeypatch):
    home = tmp_path
    input_dir = home / "input"
    input_dir.mkdir()
    checked_dir = home / "checked"
    checked_dir.mkdir()
    reports_dir = home / "reports"
    reports_dir.mkdir()

    df_in = pd.DataFrame({"email": ["a@example.com", "b@example.com"]})
    df_in.to_excel(input_dir / "Receivers.xlsx", index=False)
    pd.DataFrame({"email": ["a@example.com"]}).to_excel(checked_dir / "old.xlsx", index=False)

    monkeypatch.setenv("CLEANMAILER_HOME", str(home))
    mod = load_module()
    mod.filter_existing()

    out = pd.read_excel(reports_dir / "kontrol_edilmemis.xlsx")
    assert out["email"].tolist() == ["b@example.com"]
