"""
Configuration Management for Banking Agentic AI System

WHY THIS FILE EXISTS:
- Centralized configuration (one place to change settings)
- Type safety (Pydantic catches configuration errors early)
- Environment-based settings (dev/staging/prod)
- Secure credential management

LEARNING POINTS:
- Using Pydantic for configuration validation
- Environment variable loading
- Type hints for better code quality
- Default values and validation
"""

import os
from typing import Literal
from pydantic import Field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
from dotenv import load_dotenv

# Explicitly load .env file before anything else
# This ensures environment variables are available when Pydantic loads
load_dotenv()


class GeminiConfig(BaseSettings):
    """
    Google Gemini LLM Configuration
    
    WHY: Gemini is our AI "brain" - we need to configure:
    - API key (authentication)
    - Model selection (speed vs capability)
    - Rate limits (free tier has limits)
    """
    
    # Field() provides metadata and validation
    # alias="GEMINI_API_KEY" means it reads from .env file
    api_key: str = Field(
        ...,  # ... means REQUIRED (no default)
        alias="GEMINI_API_KEY",
        description="Google Gemini API key from makersuite.google.com"
    )
    
    # Literal[] restricts to specific values only
    # Prevents typos like "gemini-1.5-flahs" (catches errors early!)
    model: Literal["gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro", "gemini-2.5-flash-lite"] = Field(
        default="gemini-1.5-flash",
        alias="GEMINI_MODEL",
        description="Gemini model to use. Flash is faster and free."
    )
    
    # Validator - custom validation logic
    @validator('api_key')
    def validate_api_key(cls, v):
        """
        WHY: Catch configuration errors immediately
        Better to fail fast than get cryptic API errors later
        """
        if v == "your_gemini_api_key_here":
            raise ValueError(
                "Please set your real Gemini API key in .env file!\n"
                "Get it from: https://makersuite.google.com/app/apikey"
            )
        if not v.strip():
            raise ValueError("API key cannot be empty")
        return v.strip()


class EmbeddingConfig(BaseSettings):
    """
    Embedding Model Configuration
    
    WHY EMBEDDINGS:
    - Convert text to numbers (vectors)
    - Enable similarity search (core of RAG)
    - Example: "checking account" and "current account" have similar embeddings
    
    WHY SENTENCE-TRANSFORMERS:
    - Runs locally (FREE)
    - No API calls needed
    - Fast and accurate
    """
    
    provider: Literal["sentence_transformers"] = Field(
        default="sentence_transformers",
        alias="EMBEDDING_PROVIDER"
    )
    
    # all-MiniLM-L6-v2: Small (80MB), fast, good quality
    # Other options: all-mpnet-base-v2 (larger, more accurate)
    model_name: str = Field(
        default="all-MiniLM-L6-v2",
        alias="EMBEDDING_MODEL",
        description="HuggingFace embedding model"
    )


class VectorDBConfig(BaseSettings):
    """
    Vector Database Configuration
    
    WHY VECTOR DATABASE:
    - Stores document embeddings
    - Fast similarity search (finds relevant documents)
    - Core component of RAG (Retrieval-Augmented Generation)
    
    WHY FAISS:
    - Facebook's library (fast, reliable)
    - Runs in-memory (no setup needed)
    - Perfect for development
    """
    
    db_type: Literal["faiss", "chroma"] = Field(
        default="faiss",
        alias="VECTOR_DB_TYPE"
    )
    
    # Path where we save the index (persists between runs)
    faiss_index_path: str = Field(
        default="data/processed/faiss_index",
        alias="FAISS_INDEX_PATH"
    )


class ModelConfig(BaseSettings):
    """
    LLM Generation Parameters
    
    WHY THESE PARAMETERS:
    - Control response quality, length, creativity
    - Balance between cost and quality
    - Banking needs consistency (lower temperature)
    """
    
    # Maximum response length in tokens
    # 1 token ≈ 4 characters in English
    # 2048 tokens ≈ 1500 words (plenty for banking responses)
    max_tokens: int = Field(
        default=2048,
        alias="MAX_TOKENS",
        ge=100,  # Greater than or equal to 100
        le=8192  # Less than or equal to 8192 (Gemini limit)
    )
    
    # Temperature: 0.0 = deterministic, 1.0 = creative
    # Banking: we want consistent, reliable answers (0.7 is good)
    # Creative writing: might use 0.9-1.0
    temperature: float = Field(
        default=0.7,
        alias="TEMPERATURE",
        ge=0.0,
        le=1.0
    )
    
    # Top-p (nucleus sampling): alternative to temperature
    # 0.9 means "use top 90% probable words"
    # Lower = more focused, Higher = more diverse
    top_p: float = Field(
        default=0.9,
        alias="TOP_P",
        ge=0.0,
        le=1.0
    )


class AppConfig(BaseSettings):
    """
    Main Application Configuration
    
    WHY THIS CLASS:
    - Single source of truth for all settings
    - Loads from .env file automatically
    - Type checking prevents bugs
    - Easy to test with different configs
    """
    
    # Tell Pydantic where to find .env file
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,  # API_KEY = api_key
        extra="ignore",  # Ignore extra fields in .env
        env_nested_delimiter="__"  # For nested configs
    )
    
    # Environment: development, staging, or production
    # WHY: Different behaviors in different environments
    # - Dev: detailed logging, no caching
    # - Prod: minimal logging, aggressive caching
    environment: Literal["development", "staging", "production"] = Field(
        default="development",
        alias="ENVIRONMENT"
    )
    
    # Log level controls verbosity
    # DEBUG: Everything (useful for troubleshooting)
    # INFO: Important events
    # WARNING: Potential issues
    # ERROR: Only errors
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO",
        alias="LOG_LEVEL"
    )
    
    # Banking specific
    bank_name: str = Field(
        default="DemoBank",
        alias="BANK_NAME"
    )
    
    # Compliance mode affects prompt engineering
    # strict: More formal, risk-averse responses
    # standard: Balanced
    compliance_mode: Literal["strict", "standard"] = Field(
        default="standard",
        alias="COMPLIANCE_MODE"
    )
    
    # Cost tracking (important for production!)
    track_costs: bool = Field(
        default=True,
        alias="TRACK_COSTS"
    )
    
    # Sub-configurations (composition pattern)
    # WHY: Organize related settings together
    gemini: GeminiConfig = Field(default_factory=GeminiConfig)
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    vector_db: VectorDBConfig = Field(default_factory=VectorDBConfig)
    model: ModelConfig = Field(default_factory=ModelConfig)
    
    def __init__(self, **kwargs):
        """
        Initialize configuration
        
        WHY __init__: Custom initialization logic
        Loads sub-configs automatically
        """
        super().__init__(**kwargs)
        # Initialize sub-configurations
        self.gemini = GeminiConfig()
        self.embedding = EmbeddingConfig()
        self.vector_db = VectorDBConfig()
        self.model = ModelConfig()
    
    @property
    def is_development(self) -> bool:
        """Helper property for checking environment"""
        return self.environment == "development"
    
    @property
    def is_production(self) -> bool:
        """Helper property for checking environment"""
        return self.environment == "production"
    
    def get_cost_info(self) -> str:
        """
        Get cost information for current setup
        
        WHY: Helps track expenses and make informed decisions
        """
        return (
            f"💰 Cost Estimate:\n"
            f"   Gemini {self.gemini.model}: FREE (60 req/min)\n"
            f"   Embeddings: FREE (runs locally)\n"
            f"   Vector DB: FREE (runs locally)\n"
            f"   Total: $0.00/month 🎉"
        )


# Global configuration instance
# WHY GLOBAL: Configuration is loaded once at startup
# All modules import this single instance
# Prevents reloading .env file multiple times
config = AppConfig()


def get_config() -> AppConfig:
    """
    Get the global configuration instance
    
    WHY THIS FUNCTION:
    - Explicit is better than implicit (Python Zen)
    - Easier to mock in tests
    - Clear intent: "I'm getting config"
    
    USAGE:
        from src.utils.config import get_config
        
        config = get_config()
        print(config.gemini.model)
    """
    return config


# Test code - runs only when you execute this file directly
# python -m src.utils.config
if __name__ == "__main__":
    print("\n" + "="*60)
    print("🏦 Banking Agentic AI - Configuration Test")
    print("="*60 + "\n")
    
    try:
        cfg = get_config()
        
        print("✅ Configuration loaded successfully!\n")
        print(f"📊 Settings:")
        print(f"   Environment: {cfg.environment}")
        print(f"   Log Level: {cfg.log_level}")
        print(f"   Bank Name: {cfg.bank_name}")
        print(f"\n🤖 Gemini LLM:")
        print(f"   Model: {cfg.gemini.model}")
        print(f"   API Key: {'✓ Set' if cfg.gemini.api_key else '✗ Not Set'}")
        print(f"\n🔢 Embeddings:")
        print(f"   Provider: {cfg.embedding.provider}")
        print(f"   Model: {cfg.embedding.model_name}")
        print(f"\n💾 Vector Database:")
        print(f"   Type: {cfg.vector_db.db_type}")
        print(f"   Index Path: {cfg.vector_db.faiss_index_path}")
        print(f"\n⚙️  Generation Parameters:")
        print(f"   Max Tokens: {cfg.model.max_tokens}")
        print(f"   Temperature: {cfg.model.temperature}")
        print(f"   Top P: {cfg.model.top_p}")
        print(f"\n{cfg.get_cost_info()}")
        
    except Exception as e:
        print(f"❌ Configuration Error:")
        print(f"   {str(e)}\n")
        print("💡 Fix: Check your .env file and ensure all required values are set")
        exit(1)
