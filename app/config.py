import os


class Config:
    DATABASE = os.environ.get("EVENTHUB_DB", "eventhub.db")
    JSON_SORT_KEYS = False
