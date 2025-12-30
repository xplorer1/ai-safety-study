"""
PostgreSQL Database Configuration for AI Village v4.
Supports environment variables for secure credential management.
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class DatabaseConfig:
    """PostgreSQL connection configuration."""
    host: str = "localhost"
    port: int = 5432
    database: str = "ai_village"
    user: str = "postgres"
    password: str = "postgres"
    min_pool_size: int = 5
    max_pool_size: int = 20
    
    @classmethod
    def from_env(cls) -> "DatabaseConfig":
        """Load configuration from environment variables."""
        return cls(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            database=os.getenv("POSTGRES_DB", "ai_village"),
            user=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD", "delta"),
            min_pool_size=int(os.getenv("POSTGRES_MIN_POOL", "5")),
            max_pool_size=int(os.getenv("POSTGRES_MAX_POOL", "20")),
        )
    
    @property
    def dsn(self) -> str:
        """Return connection DSN string."""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


# Global config instance
db_config = DatabaseConfig.from_env()
