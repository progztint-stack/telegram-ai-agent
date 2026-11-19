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
        host = (parsed.hostname or "").lower().strip(".")
        if not host:
            raise NavigationDeniedError("عنوان الموقع غير صالح")

        local_names = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}
        if host not in local_names:
            try:
                resolved_addresses = {
                    address[4][0]
                    for address in socket.getaddrinfo(host, parsed.port, type=socket.SOCK_STREAM)
                }
            except (socket.gaierror, ValueError):
                resolved_addresses = set()
        else:
            resolved_addresses = {host}

        if not resolved_addresses:
            raise NavigationDeniedError("تعذر التحقق من عنوان الموقع")

        try:
            contains_private_address = any(
                (address := ipaddress.ip_address(resolved_address)).is_private
                or address.is_loopback
                or address.is_link_local
                for resolved_address in resolved_addresses
            )
        except ValueError:
            contains_private_address = False

        if (host in local_names or contains_private_address) and not self.allow_local:
            raise NavigationDeniedError("الشبكات المحلية ونطاقات البيانات السحابية محظورة")

        allowed = host in self.allowed_domains or any(
            host.endswith("." + domain) for domain in self.allowed_domains
        )
        if not allowed:
            raise NavigationDeniedError("النطاق غير موجود في قائمة المواقع المسموحة")
        return url
