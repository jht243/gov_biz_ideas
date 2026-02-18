import os
import json
import logging

logger = logging.getLogger(__name__)

CACHE_FILE = os.path.join(os.path.dirname(__file__), 'analysis_cache.json')


class BillCache:
    """
    A simple file-backed cache for bill analysis results.
    
    Key: "{state}:{bill_id}"
    Value: { "updated_at": str, "analysis": dict }
    
    A cache hit occurs when the bill_id exists AND the updated_at
    timestamp matches. If the bill has been updated since last analysis,
    we treat it as a miss so it gets re-analyzed.
    """

    def __init__(self, cache_path=None):
        self.cache_path = cache_path or CACHE_FILE
        self.data = {}
        self.hits = 0
        self.misses = 0
        self._load()

    def _load(self):
        """Load cache from disk."""
        if os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, 'r') as f:
                    self.data = json.load(f)
                logger.info(f"Cache loaded: {len(self.data)} entries from {self.cache_path}")
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load cache ({e}), starting fresh.")
                self.data = {}
        else:
            logger.info("No cache file found. Starting with empty cache.")

    def save(self):
        """Persist cache to disk."""
        try:
            with open(self.cache_path, 'w') as f:
                json.dump(self.data, f, indent=2)
            logger.info(f"Cache saved: {len(self.data)} entries to {self.cache_path}")
        except IOError as e:
            logger.error(f"Failed to save cache: {e}")

    def _make_key(self, bill):
        """Create a unique cache key from a bill dict."""
        state = bill.get('state', 'unknown')
        bill_id = bill.get('id', 'unknown')
        return f"{state}:{bill_id}"

    def get(self, bill):
        """
        Look up a bill in cache. Returns the cached analysis result
        if the bill hasn't been updated since last analysis, else None.
        """
        key = self._make_key(bill)
        entry = self.data.get(key)

        if entry is None:
            self.misses += 1
            return None

        # Check if the bill has been updated since we last analyzed it
        cached_updated_at = entry.get('updated_at', '')
        current_updated_at = bill.get('updated_at', '')

        if cached_updated_at == current_updated_at:
            self.hits += 1
            logger.info(f"  CACHE HIT: {key}")
            return entry.get('analysis')
        else:
            self.misses += 1
            logger.info(f"  CACHE MISS (stale): {key}")
            return None

    def set(self, bill, analysis):
        """Store an analysis result in the cache."""
        key = self._make_key(bill)
        self.data[key] = {
            'updated_at': bill.get('updated_at', ''),
            'analysis': analysis
        }

    def stats(self):
        """Return a human-readable summary of cache performance."""
        total = self.hits + self.misses
        if total == 0:
            return "Cache: no lookups performed."
        hit_rate = (self.hits / total) * 100
        return (
            f"Cache stats: {self.hits} hits, {self.misses} misses "
            f"({hit_rate:.0f}% hit rate). "
            f"Saved {self.hits} OpenAI API call(s)."
        )
