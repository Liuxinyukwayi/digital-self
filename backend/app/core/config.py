from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # 应用配置
    APP_NAME: str = "Digital Self"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True

    # 数据库配置
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/digital_self"

    # Qdrant配置
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION: str = "digital_self_memories"
    QDRANT_ENABLED: bool = True

    # Redis配置
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    # 当前使用的模型提供商: mimo, deepseek, openai
    ACTIVE_PROVIDER: str = "mimo"

    # MIMO API配置
    MIMO_API_KEY: Optional[str] = None
    MIMO_API_BASE: str = "https://api.xiaomimimo.com/v1"
    MIMO_MODEL: str = "mimo-v2.5-pro"

    # DeepSeek配置
    DEEPSEEK_API_KEY: Optional[str] = None
    DEEPSEEK_API_BASE: str = "https://api.deepseek.com/v1"
    DEEPSEEK_MODEL: str = "deepseek-chat"

    # OpenAI配置
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_API_BASE: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-large"

    # 自定义Provider配置
    CUSTOM_API_BASE: str = ""
    CUSTOM_API_KEY: Optional[str] = None
    CUSTOM_MODEL: str = ""

    # Embedding配置
    EMBEDDING_MODE: str = "lite"
    EMBEDDING_DIMENSION: int = 1024
    EMBEDDING_BATCH_SIZE: int = 64

    # Ollama配置（Full模式）
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # LightRAG配置
    LIGHTRAG_ENABLED: bool = True
    LIGHTRAG_WORKING_DIR: str = "../data/lightrag"
    LIGHTRAG_QUERY_MODE: str = "hybrid"

    # 记忆配置
    SHORT_TERM_MEMORY_LIMIT: int = 20
    MEMORY_IMPORTANCE_THRESHOLD: int = 5
    DISTILL_SCHEDULE: str = "weekly"
    DEFAULT_USER_ID: int = 1
    DEFAULT_USER_NAME: str = "default_user"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
