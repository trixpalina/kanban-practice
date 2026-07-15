from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Используем SQLite для мгновенного старта без установки PostgreSQL!
    # Файл базы данных kanban.db создастся автоматически в папке backend
    DATABASE_URL: str = "sqlite:///./kanban.db"
    
    # Если позже захочешь PostgreSQL, просто закомментируй строку выше и раскомментируй эту:
    # DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/kanban_db"

    SECRET_KEY: str = "your-super-secret-key-for-jwt"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    class Config:
        env_file = ".env"

settings = Settings()