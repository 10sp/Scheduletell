from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    database_url: str
    
    # JWT
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Cal.com
    calcom_api_key: Optional[str] = None
    calcom_base_url: str = "https://api.cal.com/v1"
    
    class Config:
        env_file = ".env"


settings = Settings()