"""애플리케이션 설정"""
from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """환경 설정"""

    # App
    app_name: str = "Auction AI Agent"
    debug: bool = False

    # API Keys
    anthropic_api_key: str = Field(default="", env="ANTHROPIC_API_KEY")
    openai_api_key: str = Field(default="", env="OPENAI_API_KEY")

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://localhost:5432/auction",
        env="DATABASE_URL"
    )
    redis_url: str = Field(default="redis://localhost:6379", env="REDIS_URL")

    # External APIs
    court_auction_api_url: str = "https://www.courtauction.go.kr"
    molit_api_key: str = Field(default="", env="MOLIT_API_KEY")
    kakao_api_key: str = Field(default="", env="KAKAO_API_KEY")

    # Agent Settings
    default_llm_model: str = "claude-sonnet-4-20250514"
    high_reasoning_model: str = "claude-opus-4-20250514"
    max_retries: int = 3
    request_timeout: int = 60

    # Rate Limiting
    court_auction_rate_limit: float = 1.0  # requests per second
    api_rate_limit: float = 10.0

    # Paths
    output_dir: str = "./outputs"
    cache_dir: str = "./cache"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """캐시된 설정 반환"""
    return Settings()
