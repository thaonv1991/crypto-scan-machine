from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    app_name: str = "Crypto Scan Machine"
    app_env: str = "development"
    log_level: str = "INFO"
    api_rate_limit: int = 100

    # Database
    database_url: str = "postgresql+asyncpg://cryptoscan:cryptoscan_pass@localhost:5432/cryptoscan"
    database_url_sync: str = "postgresql://cryptoscan:cryptoscan_pass@localhost:5432/cryptoscan"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # MinIO
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin123"
    minio_bucket: str = "cryptoscan"

    # Telegram
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # AI APIs
    deepseek_api_key: str = ""
    gemini_api_key: str = ""
    openai_api_key: str = ""

    # External APIs
    coingecko_api_key: str = ""
    etherscan_api_key: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
