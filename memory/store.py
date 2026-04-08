import json
import os
from datetime import datetime

class MemoryStore:
    """Per-user memory store backed by a JSON file."""

    def __init__(self, file_path="memory/user_default.json"):
        self.file_path = file_path
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        self._ensure_file()

    def _ensure_file(self):
        if not os.path.exists(self.file_path):
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump({"facts": [], "preferences": []}, f, indent=4)

    def load_memory(self):
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {"facts": [], "preferences": []}

    def save_memory(self, memory_data):
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(memory_data, f, indent=4)

    # ── helpers ────────────────────────────────────────────
    def _make_entry(self, text, importance=3):
        return {
            "text": text,
            "added_at": datetime.utcnow().isoformat(),
            "importance": importance
        }

    def _get_text(self, entry):
        """Support both legacy plain strings and new dict format."""
        return entry["text"] if isinstance(entry, dict) else entry

    # ── add / update ──────────────────────────────────────
    def update_memory(self, new_facts, new_prefs, importance=3):
        mem = self.load_memory()
        existing_fact_texts = [self._get_text(e) for e in mem["facts"]]
        existing_pref_texts = [self._get_text(e) for e in mem["preferences"]]

        for f in new_facts:
            if f not in existing_fact_texts:
                mem["facts"].append(self._make_entry(f, importance))

        for p in new_prefs:
            if p not in existing_pref_texts:
                mem["preferences"].append(self._make_entry(p, importance))

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

    # ── search ────────────────────────────────────────────
    def search_memory(self, query: str):
        q = query.lower().strip()
        mem = self.load_memory()
        def match(entry):
            return q in self._get_text(entry).lower()
        return {
            "facts": [e for e in mem["facts"] if match(e)],
            "preferences": [e for e in mem["preferences"] if match(e)]
        }

    # ── stats helpers ─────────────────────────────────────
    def get_all_texts(self):
        mem = self.load_memory()
        return (
            [self._get_text(e) for e in mem["facts"]],
            [self._get_text(e) for e in mem["preferences"]]
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

    def remove_fact(self, fact):
        mem = self.load_memory()
        mem["facts"] = [e for e in mem["facts"] if self._get_text(e) != fact]
        self.save_memory(mem)
