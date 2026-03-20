#!/usr/bin/env python3
"""
OPMALab · Common Utility Functions
Avoids duplicate definitions of read_json, now_iso, etc. across scripts
"""
import json, pathlib, datetime, re
from urllib.parse import urlparse
import ipaddress


def read_json(path, default=None):
    """Safely read JSON file, return default on failure."""
    try:
        return json.loads(pathlib.Path(path).read_text())
    except Exception:
        return default if default is not None else {}


def now_iso():
    """Return UTC ISO 8601 timestamp string (with Z suffix)."""
    return datetime.datetime.now(datetime.timezone.utc).isoformat().replace('+00:00', 'Z')


def today_str(fmt='%Y%m%d'):
    """Return today's date as string, default YYYYMMDD."""
    return datetime.date.today().strftime(fmt)


def safe_name(s: str) -> bool:
    """Check if name contains only safe characters (letters, digits, underscore, hyphen, Chinese)."""
    return bool(re.match(r'^[a-zA-Z0-9_\-]+$', s))


def validate_url(url: str, allowed_schemes=('https',), allowed_domains=None) -> bool:
    """Validate URL safety, prevent SSRF attacks."""
    try:
        parsed = urlparse(url)
        if parsed.scheme not in allowed_schemes:
            return False
        if allowed_domains and parsed.hostname not in allowed_domains:
            return False
        if not parsed.hostname:
            return False

        # Check if hostname is a private/reserved IP
        try:
            ip = ipaddress.ip_address(parsed.hostname)
            if ip.is_private or ip.is_loopback or ip.is_reserved:
                return False
        except ValueError:
            pass  # hostname is not an IP, which is fine
        
        return True
    except Exception:
        return False
