"""
Memory Decay Engine
Memories lose importance over time unless they are frequently accessed.
Run this periodically (e.g. nightly) via APScheduler.
"""
from datetime import datetime


class MemoryDecay:
    """
    Applies exponential decay to importance scores.
    Formula: importance = base * (1 - rate)^days + access_bonus
    """

    @staticmethod
    def apply_decay(memories, decay_rate=0.04):
        """
        memories: dict from MemoryStore.load_memory()
        decay_rate: importance lost per day (default 4%)
        Returns the updated memories dict.
        """
        now = datetime.utcnow()
        categories = ["facts", "preferences", "goals"]

        for cat in categories:
            for item in memories.get(cat, []):
                if not isinstance(item, dict):
                    continue

                # Parse timestamp
                ts_str = item.get("added_at", str(now))
                try:
                    ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00").replace("+00:00", ""))
                except Exception:
                    ts = now

                days_since = max(0, (now - ts).days)

                # Base importance on a 1-5 scale, normalise to 0-1 for calculation
                raw = item.get("importance", 3)
                base = raw / 5.0  # normalise to [0,1]

                # Access bonus: each access adds 5% up to +30%
                access_bonus = min(item.get("access_count", 0) * 0.05, 0.30)

                # Decay
                decayed = base * ((1 - decay_rate) ** days_since) + access_bonus
                decayed = max(0.01, min(1.0, decayed))

                # Convert back to 1-5 scale, keep at least 1
                item["importance"] = max(1, round(decayed * 5))

        return memories


def process_decay(memory_store):
    """Run decay on a memory store and save the result."""
    memories = memory_store.load_memory()
    decayed = MemoryDecay.apply_decay(memories)
    memory_store.save_memory(decayed)
    print(f"[MemoryDecay] Decay applied to {memory_store.file_path}")
