import pytest
from unittest.mock import patch

from src.browser.security import BrowserSecurity, NavigationDeniedError


def test_allowlist_accepts_subdomain():
    security = BrowserSecurity({"example.com"}, allow_local=True)
    addresses = [(2, 1, 6, "", ("93.184.216.34", 443))]
    with patch("src.browser.security.socket.getaddrinfo", return_value=addresses):
        assert security.validate_url("https://shop.example.com/test") == "https://shop.example.com/test"


def test_allowlist_rejects_unknown_domain():
    security = BrowserSecurity({"example.com"})
    with pytest.raises(NavigationDeniedError):
        security.validate_url("https://unknown.test/page")


def test_localhost_blocked_by_default():
    security = BrowserSecurity({"localhost"}, allow_local=False)
    with pytest.raises(NavigationDeniedError):
        security.validate_url("http://localhost:8080")


@pytest.mark.parametrize("url", [
    "http://127.0.0.1/",
    "http://10.0.0.1/",
    "http://169.254.169.254/latest/meta-data",
])
def test_private_networks_blocked(url):
    security = BrowserSecurity({"127.0.0.1", "10.0.0.1", "169.254.169.254"}, allow_local=False)
    with pytest.raises(NavigationDeniedError):
        security.validate_url(url)


def test_dns_name_rejects_when_any_resolved_address_is_private():
    security = BrowserSecurity({"example.test"}, allow_local=False)
    addresses = [
        (2, 1, 6, "", ("93.184.216.34", 443)),
        (2, 1, 6, "", ("10.0.0.25", 443)),
    ]
    with patch("src.browser.security.socket.getaddrinfo", return_value=addresses):
        with pytest.raises(NavigationDeniedError):
            security.validate_url("https://example.test/")
