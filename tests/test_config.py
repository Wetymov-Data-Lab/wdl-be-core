import pytest
from pydantic import ValidationError

from wdl_be_core.infrastructure.config import Settings


def test_boolean_settings_are_parsed_from_strings() -> None:
    settings = Settings(DEBUG="False", CORS_DISABLE="True")  # type: ignore[arg-type]

    assert settings.DEBUG is False
    assert settings.CORS_DISABLE is True


@pytest.mark.parametrize(
    ("override", "message"),
    [
        (
            {"JWT_SECRET_KEY": "development-only-change-me-at-least-32-chars"},
            "JWT_SECRET_KEY must be changed",
        ),
        ({"POSTGRES_PASSWORD": "postgres"}, "POSTGRES_PASSWORD must be changed"),
        (
            {"DEBUG": True},
            "DEBUG must be disabled",
        ),
        (
            {"CORS_REGEX": ".*"},
            "Wildcard CORS must be disabled",
        ),
    ],
)
def test_production_rejects_unsafe_settings(override: dict[str, object], message: str) -> None:
    safe = {
        "JWT_SECRET_KEY": "x" * 32,
        "POSTGRES_PASSWORD": "strong",
        "DEBUG": False,
        "CORS_DISABLE": False,
        "CORS_REGEX": r"https://.*\.wdl\.ru",
    }
    with pytest.raises(ValidationError, match=message):
        Settings(ENVIRONMENT="production", **(safe | override))
