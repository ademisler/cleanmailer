import importlib.util
import pathlib
import pytest

try:
    import dns.resolver
    from dns.exception import DNSException
except Exception:
    pytest.skip("dnspython not installed", allow_module_level=True)

# Dynamically load the module because its filename starts with a number
MODULE_PATH = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "02_check_domains.py"
spec = importlib.util.spec_from_file_location("check_domains", MODULE_PATH)
check_domains = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_domains)


def test_is_domain_active_mx_success(monkeypatch):
    def fake_resolve(domain, record):
        assert record == "MX"
        return True

    monkeypatch.setattr(dns.resolver, "resolve", fake_resolve)
    assert check_domains.is_domain_active("example.com") is True


def test_is_domain_active_a_fallback(monkeypatch):
    def fake_resolve(domain, record):
        if record == "MX":
            raise DNSException()
        return True

    monkeypatch.setattr(dns.resolver, "resolve", fake_resolve)
    assert check_domains.is_domain_active("example.com") is True


def test_is_domain_active_fail(monkeypatch):
    def fake_resolve(domain, record):
        raise DNSException()

    monkeypatch.setattr(dns.resolver, "resolve", fake_resolve)
    assert check_domains.is_domain_active("example.com") is False

