# Stub — implementation added in Plan 02
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = ""


settings = Settings()
