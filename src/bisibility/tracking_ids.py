"""Runtime extension namespaces; historical public ID types remain unchanged."""

import re

from .errors import BisibilityConfigurationError


def require_tracking_id(value: str, prefix: str) -> str:
    if prefix not in {"ait", "aip", "apr", "ais", "air", "asm"} or not re.fullmatch(
        rf"{prefix}_[a-z][a-z0-9]{{23}}", value
    ):
        raise BisibilityConfigurationError(f"Expected a {prefix}_ public ID.")
    return value
