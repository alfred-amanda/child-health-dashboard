
from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SEED_ROOT = Path('/Users/johnchen/Documents/Health/Thomas Medical Profile')


class ExternalServicesConfig(BaseModel):
    enabled: bool = False
    allow_phi: bool = False
    summary_provider: str = 'local-only'
    alert_channel: str = 'dummy-local'


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix='CHD_', env_nested_delimiter='__')

    app_name: str = 'Child Health Dashboard'
    db_url: str = Field(default=f"sqlite:///{PROJECT_ROOT / 'data' / 'child_health.db'}")
    storage_root: Path = Field(default=PROJECT_ROOT / 'data' / 'storage')
    seed_root: Path = Field(default=SEED_ROOT)
    external_services: ExternalServicesConfig = Field(default_factory=ExternalServicesConfig)


def get_settings() -> Settings:
    return Settings()
