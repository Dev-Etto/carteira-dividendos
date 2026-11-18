from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Configuração lida de backend/.env.

    sync_hour: hora local da atualização automática diária, enquanto a API estiver rodando.
    cvm_years: quantos anos de balanços da CVM baixar.
    itr_years: quantos anos de balanços trimestrais (ITR) baixar, contando o atual.
    initial_sync: baixa todos os dados ao subir a API quando o banco nunca foi atualizado.
    """

    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    database_url: str = f"sqlite:///{BACKEND_DIR / 'data' / 'carteira.db'}"
    brapi_token: str = ""
    cache_dir: Path = BACKEND_DIR / "data" / "cache"
    cors_origins: list[str] = ["http://localhost:3000"]
    sync_hour: int = 19
    enable_scheduler: bool = True
    initial_sync: bool = True
    cvm_years: int = 6
    itr_years: int = 3


@lru_cache
def get_settings() -> Settings:
    return Settings()
