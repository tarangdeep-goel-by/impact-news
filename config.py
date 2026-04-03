"""Project settings for Impact News."""

from pydantic_settings import BaseSettings, SettingsConfigDict


RSS_FEEDS: list[dict] = [
    # Indian Economy & Policy (highest signal — 50%+ relevance)
    {"name": "ET Economy", "url": "https://economictimes.indiatimes.com/news/economy/rssfeeds/1373380680.cms", "category": "economy"},
    {"name": "IE Economy", "url": "https://indianexpress.com/section/business/economy/feed/", "category": "economy"},
    {"name": "Moneycontrol Economy", "url": "https://www.moneycontrol.com/rss/economy.xml", "category": "economy"},
    # Indian Markets & Finance
    {"name": "ET Markets", "url": "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms", "category": "finance"},
    {"name": "NDTV Profit", "url": "https://feeds.feedburner.com/ndtvprofit-latest", "category": "finance"},
    {"name": "The Hindu Business", "url": "https://www.thehindubusinessline.com/feeder/default.rss", "category": "finance"},
    {"name": "Livemint", "url": "https://www.livemint.com/rss/news", "category": "finance"},
    # Indian Business & Startups
    {"name": "Inc42", "url": "https://inc42.com/feed/", "category": "startups"},
    {"name": "IE Business", "url": "https://indianexpress.com/section/business/feed/", "category": "business"},
    # India News & Geopolitics
    {"name": "NDTV India", "url": "https://feeds.feedburner.com/ndtvnews-india-news", "category": "india"},
    {"name": "NDTV World", "url": "https://feeds.feedburner.com/ndtvnews-world-news", "category": "world"},
    {"name": "Reuters India", "url": "https://feeds.reuters.com/reuters/INtopNews", "category": "india"},
]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # API keys
    gemini_api_key: str = ""
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # Paths
    graph_path: str = "data/merged_graph.yaml"
    db_path: str = "data/impact_news.db"

    # Schedule
    collect_interval_hours: int = 2

    # Scoring
    score_high_threshold: float = 0.5
    score_medium_threshold: float = 0.2

    # LLM engine
    gemini_model: str = "gemini-3.1-flash-lite-preview"
    gemini_pro_model: str = "gemini-3.1-pro-preview"

    # Delivery
    digest_hour: int = 8
    pipeline_interval_seconds: int = 7200


settings = Settings()
