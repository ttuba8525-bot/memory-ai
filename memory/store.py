import json
import os
import shutil
from datetime import datetime


class MemoryStore:
    """Per-user memory store backed by a JSON file.
    Supports: facts, preferences, goals.
    Features: backup/auto-repair, decay-ready importance scores.
    """

    def __init__(self, file_path="memory/user_default.json"):
        self.file_path = file_path
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        self._ensure_file()

    # ── File init ──────────────────────────────────────────
    def _ensure_file(self):
        if not os.path.exists(self.file_path):
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump({"facts": [], "preferences": [], "goals": []}, f, indent=4)

    def _backup_memory(self, data):
        """Save a timestamped backup of valid memory data."""
        backup_path = f"{self.file_path}.backup"
        try:
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"[MemoryStore] Backup failed: {e}")

    def _repair_corrupted_memory(self):
        """Attempt to restore memory from backup file."""
        backup_path = f"{self.file_path}.backup"
        if os.path.exists(backup_path):
            try:
                shutil.copy(backup_path, self.file_path)
                print(f"[MemoryStore] Auto-repaired {self.file_path} from backup.")
                return True
            except Exception as e:
                print(f"[MemoryStore] Repair failed: {e}")
        return False

    def _normalize(self, data):
        """Ensure all entries are dicts with required fields. Handles legacy plain strings."""
        categories = ["facts", "preferences", "goals"]
        now = datetime.utcnow().isoformat()
        normalized = {}
        for cat in categories:
            normalized[cat] = []
            for item in data.get(cat, []):
                if isinstance(item, str):
                    normalized[cat].append({
                        "text": item,
                        "added_at": now,
                        "importance": 3,
                        "access_count": 0
                    })
                else:
                    if "text" not in item and "content" in item:
                        item["text"] = item.pop("content")  # migrate from memory-ai format
                    if "added_at" not in item:
                        item["added_at"] = now
                    if "importance" not in item:
                        item["importance"] = 3
                    if "access_count" not in item:
                        item["access_count"] = 0
                    normalized[cat].append(item)
        return normalized

    # ── Load ───────────────────────────────────────────────
    def load_memory(self):
        try:
            if not os.path.exists(self.file_path) or os.path.getsize(self.file_path) == 0:
                if self._repair_corrupted_memory():
                    with open(self.file_path, 'r', encoding='utf-8') as f:
                        return self._normalize(json.load(f))
                return {"facts": [], "preferences": [], "goals": []}

            with open(self.file_path, 'r', encoding='utf-8') as f:
                try:
                    data = json.load(f)
                    # Ensure goals key exists (migration for old files)
                    if "goals" not in data:
                        data["goals"] = []
                    norm = self._normalize(data)
                    self._backup_memory(norm)
                    return norm
                except Exception:
                    print(f"[MemoryStore] JSON decode failed, attempting repair.")
                    if self._repair_corrupted_memory():
                        with open(self.file_path, 'r', encoding='utf-8') as f2:
                            return self._normalize(json.load(f2))
                    return {"facts": [], "preferences": [], "goals": []}
        except Exception as e:
            print(f"[MemoryStore] Load failed: {e}")
            return {"facts": [], "preferences": [], "goals": []}

    # ── Save ───────────────────────────────────────────────
    def save_memory(self, memory_data):
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(memory_data, f, indent=4, ensure_ascii=False)

    # ── Helpers ────────────────────────────────────────────
    def _make_entry(self, text, importance=3):
        return {
            "text": text,
            "added_at": datetime.utcnow().isoformat(),
            "importance": importance,
            "access_count": 0
        }

    def _get_text(self, entry):
        """Support both legacy plain strings and dict format."""
        if isinstance(entry, dict):
            return entry.get("text") or entry.get("content", "")
        return str(entry)

    # ── Update ─────────────────────────────────────────────
    def update_memory(self, new_facts, new_prefs, new_goals=None, importance=3):
        mem = self.load_memory()
        existing_fact_texts  = [self._get_text(e) for e in mem["facts"]]
        existing_pref_texts  = [self._get_text(e) for e in mem["preferences"]]
        existing_goal_texts  = [self._get_text(e) for e in mem["goals"]]

        for f in (new_facts or []):
            if f not in existing_fact_texts:
                mem["facts"].append(self._make_entry(f, importance))
        for p in (new_prefs or []):
            if p not in existing_pref_texts:
                mem["preferences"].append(self._make_entry(p, importance))
        for g in (new_goals or []):
            if g not in existing_goal_texts:
                mem["goals"].append(self._make_entry(g, importance))

        self.save_memory(mem)

    def update_fact(self, idx, new_text):
        mem = self.load_memory()
        if 0 <= idx < len(mem["facts"]):
            entry = mem["facts"][idx]
            if isinstance(entry, dict):
                entry["text"] = new_text
            else:
                mem["facts"][idx] = self._make_entry(new_text)
        self.save_memory(mem)

    def update_pref(self, idx, new_text):
        mem = self.load_memory()
        if 0 <= idx < len(mem["preferences"]):
            entry = mem["preferences"][idx]
            if isinstance(entry, dict):
                entry["text"] = new_text
            else:
                mem["preferences"][idx] = self._make_entry(new_text)
        self.save_memory(mem)

    def update_goal(self, idx, new_text):
        mem = self.load_memory()
        if 0 <= idx < len(mem["goals"]):
            entry = mem["goals"][idx]
            if isinstance(entry, dict):
                entry["text"] = new_text
            else:
                mem["goals"][idx] = self._make_entry(new_text)
        self.save_memory(mem)

    def delete_fact(self, idx):
        mem = self.load_memory()
        if 0 <= idx < len(mem["facts"]):
            mem["facts"].pop(idx)
        self.save_memory(mem)

    def delete_pref(self, idx):
        mem = self.load_memory()
        if 0 <= idx < len(mem["preferences"]):
            mem["preferences"].pop(idx)
        self.save_memory(mem)

    def delete_goal(self, idx):
        mem = self.load_memory()
        if 0 <= idx < len(mem["goals"]):
            mem["goals"].pop(idx)
        self.save_memory(mem)

    # ── Search ─────────────────────────────────────────────
    def search_memory(self, query: str):
        q = query.lower().strip()
        mem = self.load_memory()
        def match(entry):
            return q in self._get_text(entry).lower()
        return {
            "facts":       [e for e in mem["facts"]       if match(e)],
            "preferences": [e for e in mem["preferences"] if match(e)],
            "goals":       [e for e in mem["goals"]       if match(e)],
        }

    # ── Stats helpers ──────────────────────────────────────
    def get_all_texts(self):
        mem = self.load_memory()
        return (
            [self._get_text(e) for e in mem["facts"]],
            [self._get_text(e) for e in mem["preferences"]],
            [self._get_text(e) for e in mem["goals"]],
        )

    def add_fact(self, fact, importance=3):
        mem = self.load_memory()
        texts = [self._get_text(e) for e in mem["facts"]]
        if fact not in texts:
            mem["facts"].append(self._make_entry(fact, importance))
            self.save_memory(mem)

    def add_preference(self, pref, importance=3):
        mem = self.load_memory()
        texts = [self._get_text(e) for e in mem["preferences"]]
        if pref not in texts:
            mem["preferences"].append(self._make_entry(pref, importance))
            self.save_memory(mem)

    def add_goal(self, goal, importance=3):
        mem = self.load_memory()
        texts = [self._get_text(e) for e in mem["goals"]]
        if goal not in texts:
            mem["goals"].append(self._make_entry(goal, importance))
            self.save_memory(mem)

    def remove_fact(self, fact):
        mem = self.load_memory()
        mem["facts"] = [e for e in mem["facts"] if self._get_text(e) != fact]
        self.save_memory(mem)

    def remove_preference(self, pref):
        mem = self.load_memory()
        mem["preferences"] = [e for e in mem["preferences"] if self._get_text(e) != pref]
        self.save_memory(mem)

    def remove_goal(self, goal):
        mem = self.load_memory()
        mem["goals"] = [e for e in mem["goals"] if self._get_text(e) != goal]
        self.save_memory(mem)

    # ── Access tracking (for decay) ────────────────────────
    def increment_access(self, category, idx):
        """Called by retrieval agent to track memory usage."""
        mem = self.load_memory()
        items = mem.get(category, [])
        if 0 <= idx < len(items) and isinstance(items[idx], dict):
            items[idx]["access_count"] = items[idx].get("access_count", 0) + 1
        self.save_memory(mem)

    # ── Utility ────────────────────────────────────────────
    def has_memory(self):
        mem = self.load_memory()
        return bool(mem["facts"] or mem["preferences"] or mem["goals"])
