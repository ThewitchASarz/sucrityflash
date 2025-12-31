"""
Configuration for V2 BFF (Stateless Proxy)

V2 has NO database. Only proxy configuration.
"""
import os
from typing import Optional


class Settings:
    """V2 BFF settings - proxy only."""
    
    # App info
    APP_NAME: str = "SecurityFlash V2 BFF"
    APP_VERSION: str = "2.0.0"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    # SecurityFlash V1 connection (REQUIRED)
    SECURITYFLASH_API_URL: Optional[str] = os.getenv("SECURITYFLASH_API_URL")
    SECURITYFLASH_TIMEOUT: float = float(os.getenv("SECURITYFLASH_TIMEOUT", "30.0"))
    
    # BFF server
    PORT: int = int(os.getenv("PORT", "3001"))
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    def __init__(self):
        if not self.SECURITYFLASH_API_URL:
            print("⚠️  WARNING: SECURITYFLASH_API_URL not set")
            print("   V2 BFF requires SecurityFlash V1 to be running")
            print("   Set: export SECURITYFLASH_API_URL=http://localhost:8000")


settings = Settings()
