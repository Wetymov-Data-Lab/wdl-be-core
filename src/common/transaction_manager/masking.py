from collections.abc import Collection, Mapping
from typing import Any

DEFAULT_SENSITIVE_KEYS = frozenset(
    {"access_token", "authorization", "cookie", "password", "refresh_token", "secret", "token"}
)


def mask_sensitive_data(
    value: Mapping[str, Any],
    *,
    sensitive_keys: Collection[str] = DEFAULT_SENSITIVE_KEYS,
    replacement: str = "***",
) -> dict[str, Any]:
    """Return a recursively masked copy suitable for an audit record."""
    normalized_keys = {key.casefold() for key in sensitive_keys}

    def mask(item: Any, key: str | None = None) -> Any:
        if key is not None and key.casefold() in normalized_keys:
            return replacement
        if isinstance(item, Mapping):
            return {
                str(child_key): mask(child, str(child_key)) for child_key, child in item.items()
            }
        if isinstance(item, list | tuple):
            return [mask(child) for child in item]
        return item

    masked = mask(value)
    if not isinstance(masked, dict):
        raise TypeError("A mapping masker must produce a dictionary")
    return masked
