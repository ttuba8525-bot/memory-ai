import json
import os

class MemoryStore:
    def __init__(self, file_path="memory.json"):
        self.file_path = file_path
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

    def add_fact(self, fact):
        mem = self.load_memory()
        if fact not in mem["facts"]:
            mem["facts"].append(fact)
            self.save_memory(mem)

    def add_preference(self, pref):
        mem = self.load_memory()
        if pref not in mem["preferences"]:
            mem["preferences"].append(pref)
            self.save_memory(mem)

    def remove_fact(self, fact):
        mem = self.load_memory()
        if fact in mem["facts"]:
            mem["facts"].remove(fact)
            self.save_memory(mem)

    def update_memory(self, new_facts, new_prefs):
        mem = self.load_memory()
        mem["facts"].extend([f for f in new_facts if f not in mem["facts"]])
        mem["preferences"].extend([p for p in new_prefs if p not in mem["preferences"]])
        # Remove duplicates preserving order if needed, but extend might add dups
        mem["facts"] = list(dict.fromkeys(mem["facts"]))
        mem["preferences"] = list(dict.fromkeys(mem["preferences"]))
        self.save_memory(mem)
