"""Project settings for Impact News."""

from pydantic_settings import BaseSettings, SettingsConfigDict


RSS_FEEDS: list[dict] = [
    # Indian Markets & Finance
    {"name": "ET Markets", "url": "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms", "category": "finance"},
    {"name": "ET Economy", "url": "https://economictimes.indiatimes.com/news/economy/rssfeeds/1373380680.cms", "category": "finance"},
    {"name": "NDTV Profit", "url": "https://feeds.feedburner.com/ndtvprofit-latest", "category": "finance"},
    # Indian Business & Startups
    {"name": "Inc42", "url": "https://inc42.com/feed/", "category": "startups"},
    # Tech & AI
    {"name": "TechCrunch AI", "url": "https://techcrunch.com/category/artificial-intelligence/feed/", "category": "tech"},
    {"name": "MIT Tech Review AI", "url": "https://www.technologyreview.com/topic/artificial-intelligence/feed/", "category": "tech"},
    {"name": "Ars Technica", "url": "https://feeds.arstechnica.com/arstechnica/index", "category": "tech"},
    {"name": "Hacker News", "url": "https://hnrss.org/frontpage?points=100", "category": "tech"},
    # India Politics & News
    {"name": "ET Politics", "url": "https://economictimes.indiatimes.com/news/politics-and-nation/rssfeeds/1052732854.cms", "category": "india"},
    {"name": "NDTV India", "url": "https://feeds.feedburner.com/ndtvnews-india-news", "category": "india"},
    {"name": "NDTV World", "url": "https://feeds.feedburner.com/ndtvnews-world-news", "category": "world"},
    # New India-specific sources
    {"name": "Livemint", "url": "https://www.livemint.com/rss/news", "category": "finance"},
    {"name": "The Hindu Business", "url": "https://www.thehindubusinessline.com/feeder/default.rss", "category": "finance"},
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
    embeddings_path: str = "data/"

    # Embedding
    embedding_model: str = "all-MiniLM-L6-v2"
    match_threshold: float = 0.55

    # Graph
    max_hops: int = 3
    hub_dampening_threshold: int = 20

    # Schedule
    collect_interval_hours: int = 2

    # Scoring
    score_high_threshold: float = 0.5
    score_medium_threshold: float = 0.2
    indirect_weight: float = 0.7
    gemini_model: str = "gemini-2.0-flash"

    # PPR engine
    ppr_restart_prob: float = 0.20          # α — restart probability for PageRank
    ppr_prob_threshold: float = 0.005       # Min probability to consider a node impacted
    ppr_magnitude_blend: float = 0.5        # How much magnitude affects final score

    # Delivery
    digest_hour: int = 8
    pipeline_interval_seconds: int = 7200


settings = Settings()
