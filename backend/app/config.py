from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DASHSCOPE_API_KEY: str = ""
    AMAP_API_KEY: str = ""
    DATABASE_URL: str = "sqlite:///./data/turing_travel.db"
    REDIS_URL: str = "redis://localhost:6379/0"
    LOG_LEVEL: str = "INFO"
    LLM_MODEL: str = "deepseek-v4-pro"
    EMBEDDING_MODEL: str = "text-embedding-v4"
    RERANK_MODEL: str = "qwen3-rerank"
    CHROMA_PERSIST_DIR: str = "./chroma_data"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
