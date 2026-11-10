import os


class DefaultConfig:
    SQLALCHEMY_DATABASE_URI = os.environ.get("DB_URL", "sqlite:///week7.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}
    JSON_SORT_KEYS = False
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")


class TestConfig(DefaultConfig):
    TESTING = True
    LOG_LEVEL = "WARNING"
