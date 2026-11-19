"""Browser navigation security controls."""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse


class NavigationDeniedError(ValueError):
    pass


class BrowserSecurity:
    def __init__(
        self,
        allowed_domains: set[str],
        allow_local: bool = False,
    ) -> None:
        self.allowed_domains = {domain.lower().strip(".") for domain in allowed_domains}
        self.allow_local = allow_local

    def validate_url(self, url: str) -> str:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            raise NavigationDeniedError("يسمح فقط بروتوكولات HTTP وHTTPS")
        if parsed.username is not None or parsed.password is not None:
            raise NavigationDeniedError("بيانات تسجيل الدخول داخل العنوان غير مسموحة")
        host = (parsed.hostname or "").lower().strip(".")
        if not host:
            raise NavigationDeniedError("عنوان الموقع غير صالح")
        try:
            port = parsed.port
        except ValueError as exc:
            raise NavigationDeniedError("منفذ الموقع غير صالح") from exc

        local_names = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}
        try:
            address = ipaddress.ip_address(host)
            resolved_addresses = {address}
        except ValueError:
            try:
                resolved_addresses = {
                    ipaddress.ip_address(address[4][0])
                    for address in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
                }
            except (OSError, ValueError):
                resolved_addresses = set()

        if not resolved_addresses:
            raise NavigationDeniedError("تعذر التحقق من عنوان الموقع")

        contains_non_public_address = any(not address.is_global for address in resolved_addresses)
        if (
            (host in local_names or contains_non_public_address)
            and not self.allow_local
        ):
            raise NavigationDeniedError("الشبكات المحلية ونطاقات البيانات السحابية محظورة")

        allowed = host in self.allowed_domains or any(
            host.endswith("." + domain) for domain in self.allowed_domains
        )
        if not allowed:
            raise NavigationDeniedError("النطاق غير موجود في قائمة المواقع المسموحة")
        return url
