import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "family_assistant.db")

# LLM config
LLM_API_BASE = os.getenv("LLM_API_BASE", "https://api.openai.com/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

# Alert config
ALERT_THRESHOLD_DAYS = int(os.getenv("ALERT_THRESHOLD_DAYS", "3"))
DEFAULT_DAILY_RATE_FOR_NEW_ITEM = float(os.getenv("DEFAULT_DAILY_RATE", "0.1"))

# Feishu config
FEISHU_APP_ID = os.getenv("FEISHU_APP_ID", "")
FEISHU_APP_SECRET = os.getenv("FEISHU_APP_SECRET", "")
FEISHU_VERIFICATION_TOKEN = os.getenv("FEISHU_VERIFICATION_TOKEN", "")
FEISHU_ENCRYPT_KEY = os.getenv("FEISHU_ENCRYPT_KEY", "")
FEISHU_MODE = os.getenv("FEISHU_MODE", "webhook")  # "webhook" or "websocket"

# Product search config
SEARCH_API_KEY = os.getenv("SEARCH_API_KEY", "")
SEARCH_API_BASE = os.getenv("SEARCH_API_BASE", "https://api.bing.microsoft.com/v7.0")

# Trigger engine config
TRIGGER_SCHEDULE_HOUR = int(os.getenv("TRIGGER_SCHEDULE_HOUR", "9"))
TRIGGER_ENABLED = os.getenv("TRIGGER_ENABLED", "true").lower() == "true"

# Session config
SESSION_MAX_HISTORY = int(os.getenv("SESSION_MAX_HISTORY", "20"))
