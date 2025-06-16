from pydantic import SecretStr
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    API_KEY: SecretStr = SecretStr("")
    MODEL: str = "gemini/gemini-2.5-flash-preview-05-20"
    DB_USER: str = "postgresql"
    DB_PASSWORD: SecretStr = SecretStr("")
    DB_HOST: str = "db"
    DB_PORT: str = "5432"
    DB_NAME: str = "rag"

    @property
    def POSTGRES_URL(self):
        pwd = self.DB_PASSWORD.get_secret_value()
        return f"postgresql://{self.DB_USER}:{pwd}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"


settings = Settings()
