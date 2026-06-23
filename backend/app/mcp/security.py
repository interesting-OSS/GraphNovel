"""SSRF protection for MCP server connections."""
import ipaddress
import socket
from urllib.parse import urlparse


SSRF_BLOCKED_HOSTS = {
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "::1",
    "169.254.169.254",  # AWS metadata
    "metadata.google.internal",  # GCP metadata
}

SSRF_BLOCKED_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
]


class SSRFProtector:
    """Validates URLs to prevent Server-Side Request Forgery."""

    @staticmethod
    def is_url_safe(url: str) -> bool:
        """Check if a URL is safe from SSRF attacks.

        Returns True if the URL is allowed, False if it targets internal networks.
        """
        try:
            parsed = urlparse(url)
            hostname = parsed.hostname or ""

            # Block known internal hostnames
            if hostname.lower() in SSRF_BLOCKED_HOSTS:
                return False

            # Resolve hostname to IP and check against blocked networks
            try:
                ip = ipaddress.ip_address(hostname)
            except ValueError:
                # Try DNS resolution
                try:
                    resolved = socket.getaddrinfo(hostname, None)
                    ips = {r[4][0] for r in resolved}
                    for ip_str in ips:
                        ip = ipaddress.ip_address(ip_str)
                        for network in SSRF_BLOCKED_NETWORKS:
                            if ip in network:
                                return False
                except Exception:
                    return False
                return True

            for network in SSRF_BLOCKED_NETWORKS:
                if ip in network:
                    return False

            return True

        except Exception:
            return False

    @staticmethod
    def validate_server_url(url: str) -> str:
        """Validate and sanitize an MCP server URL.

        Raises ValueError if the URL is unsafe.
        """
        if not SSRFProtector.is_url_safe(url):
            raise ValueError(f"URL targets internal network (SSRF blocked): {url}")
        return url
