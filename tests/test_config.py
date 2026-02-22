import os
import pytest
from importlib import reload
import core.config as config

def test_default_config_values():
    assert config.OLLAMA_MODEL_CHAT == os.getenv("OLLAMA_MODEL_CHAT", "qwen3.5:cloud")
    assert config.WHISPER_MODEL_SIZE == os.getenv("WHISPER_MODEL_SIZE", "base")
    assert config.RATE_LIMIT_MESSAGES == int(os.getenv("RATE_LIMIT_MESSAGES", "20"))
    assert config.RATE_LIMIT_WINDOW == int(os.getenv("RATE_LIMIT_WINDOW", "60"))

def test_allowed_users_parsing(monkeypatch):
    monkeypatch.setenv("ALLOWED_USER_IDS", "123, 456,789")
    reload(config)
    
    assert 123 in config.ALLOWED_USER_IDS
    assert 456 in config.ALLOWED_USER_IDS
    assert 789 in config.ALLOWED_USER_IDS

def test_admin_users_parsing(monkeypatch):
    monkeypatch.setenv("ADMIN_USER_IDS", "@admin, 123, @Owner")
    reload(config)
    
    assert "admin" in config.ADMIN_USERNAMES
    assert "owner" in config.ADMIN_USERNAMES
    assert 123 in config.ADMIN_USER_IDS
