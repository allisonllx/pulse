from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import os
from dotenv import load_dotenv

COUNTRIES = {
 "SG": ("Singapore", "🇸🇬", "en"), "US": ("United States", "🇺🇸", "en"),
 "GB": ("United Kingdom", "🇬🇧", "en"), "JP": ("Japan", "🇯🇵", "ja"),
 "IN": ("India", "🇮🇳", "hi"), "BR": ("Brazil", "🇧🇷", "pt"),
 "SE": ("Sweden", "🇸🇪", "sv"), "DE": ("Germany", "🇩🇪", "de"),
 "FR": ("France", "🇫🇷", "fr"), "KR": ("South Korea", "🇰🇷", "ko"),
 "ID": ("Indonesia", "🇮🇩", "id"), "MY": ("Malaysia", "🇲🇾", "ms"),
 "AU": ("Australia", "🇦🇺", "en"), "CA": ("Canada", "🇨🇦", "en"),
 "MX": ("Mexico", "🇲🇽", "es")}
PILOT = ["SG", "US", "GB", "JP", "IN", "BR"]
EXPANSION = [c for c in COUNTRIES if c not in PILOT]
QUERIES = ["AI agents", "AI coding tools", "latest AI models", "music", "gaming"]
EXTRACTION_VERSION = "worldview-extract-3"
CAPABILITIES = {
 "instagram": {"surfaces": ["public_keyword_probe"], "profile": "english", "adapter": "http", "max_jobs": 1},
 "google_news": {"surfaces": ["local_rss", "local_html"], "profile": "local", "adapter": "http"},
 "google_search": {"surfaces": ["search_html"], "profile": "english", "adapter": "http"},
 "youtube": {"surfaces": ["search_html","gaming_discovery"], "profile": "english", "adapter": "http"},
 "tiktok": {"surfaces": ["bounded_probe"], "profile": "english", "adapter": "playwright", "max_jobs": 1}}

@dataclass
class Settings:
    data_dir: Path
    username: str = ""
    password: str = ""
    proxy_host: str = "pr.oxylabs.io"
    proxy_port: int = 7777
    budget_bytes: int = 0
    expires_at: str = ""
    host_delay_seconds: float = 2.0

    @classmethod
    def load(cls):
        # Existing environment wins; local file wins over generic .env.
        load_dotenv(".env.local", override=False)
        load_dotenv(".env", override=False)
        return cls(Path(os.getenv("WORLDVIEW_DATA_DIR", ".worldview")),
                   os.getenv("OXYLABS_USERNAME", ""), os.getenv("OXYLABS_PASSWORD", ""),
                   os.getenv("OXYLABS_PROXY_HOST", "pr.oxylabs.io"),
                   int(os.getenv("OXYLABS_PROXY_PORT", "7777")),
                   int(os.getenv("WORLDVIEW_BUDGET_BYTES", "0")),
                   os.getenv("WORLDVIEW_EXPIRES_AT", ""),
                   float(os.getenv("WORLDVIEW_HOST_DELAY_SECONDS", "2")))

    def expired(self, now=None):
        from datetime import datetime, timezone
        if not self.expires_at:
            return False
        try:
            expiry = datetime.fromisoformat(self.expires_at.replace("Z", "+00:00"))
            if expiry.tzinfo is None:
                raise ValueError()
        except ValueError:
            raise ValueError("WORLDVIEW_EXPIRES_AT must be an ISO timestamp with timezone.") from None
        return (now or datetime.now(timezone.utc)) >= expiry

    def require_live(self):
        if self.expired():
            raise ValueError("Proxy collection has expired; publish or export the existing archive.")
        if not self.username or not self.password:
            raise ValueError("Live collection requires OXYLABS_USERNAME and OXYLABS_PASSWORD in .env.local or environment.")
        if self.budget_bytes <= 0:
            raise ValueError("Live collection requires explicit WORLDVIEW_BUDGET_BYTES > 0.")
