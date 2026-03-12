from __future__ import annotations

from app.core.config import default_env_file, load_settings


def test_default_env_file_points_to_backend_env() -> None:
    env_file = default_env_file()

    assert env_file.is_absolute()
    assert env_file.name == ".env"
    assert env_file.parent.name == "backend"


def test_load_settings_reads_explicit_env_file(tmp_path, monkeypatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "COIN_LAB_APP_ENV=test",
                "COIN_LAB_STORE_BACKEND=postgres",
                "COIN_LAB_DATABASE_URL=postgresql://example",
                "COIN_LAB_LIVE_TRADING_ENABLED=true",
            ]
        ),
        encoding="utf-8",
    )

    for key in [
        "COIN_LAB_APP_ENV",
        "COIN_LAB_STORE_BACKEND",
        "COIN_LAB_DATABASE_URL",
        "COIN_LAB_LIVE_TRADING_ENABLED",
    ]:
        monkeypatch.delenv(key, raising=False)

    settings = load_settings(env_file=env_file)

    assert settings.app_env == "test"
    assert settings.store_backend == "postgres"
    assert settings.database_url == "postgresql://example"
    assert settings.live_trading_enabled is True
