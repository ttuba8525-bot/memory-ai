"""
Consolidation Agent
Runs nightly to merge similar/redundant memories and remove contradictions.
Uses the LLM to intelligently combine overlapping entries.
"""
import json
import re
from utils.llm import generate_response


class ConsolidationAgent:
    """
    Nightly memory optimizer: merges similar memories, removes redundant ones.
    Makes the memory store feel 'alive' and well-organized.
    """

    def __init__(self, memory_store):
        self.store = memory_store

    def consolidate(self):
        print("[ConsolidationAgent] Starting memory optimization...")
        memories = self.store.load_memory()
        changed = False

        for cat in ["facts", "preferences", "goals"]:
            items = memories.get(cat, [])
            if len(items) < 2:
                continue  # nothing to consolidate

            # Get plain text list
            content_list = []
            for m in items:
                if isinstance(m, dict):
                    content_list.append(m.get("text") or m.get("content", ""))
                else:
                    content_list.append(str(m))

            prompt = f"""You are a Memory Consolidation Expert for a personal AI assistant.
Review these {cat} stored in the user's memory:
{json.dumps(content_list, indent=2)}

TASK:
1. Identify items that are redundant or say the same thing in different ways.
2. Identify direct contradictions.
3. Merge redundant/similar items into a single, well-written entry.
4. Keep unique items unchanged.

Return ONLY a JSON object with NO markdown or code blocks:
{{
  "to_remove": ["exact old strings to delete"],
  "to_add": ["newly merged high-quality strings"]
}}
If nothing needs merging, return: {{"to_remove": [], "to_add": []}}
"""
            messages = [{"role": "user", "content": prompt}]
            raw = generate_response(messages, temp=0.2)

            # Strip markdown
            raw = raw.strip()
            if raw.startswith("```"):
                raw = re.sub(r"```(?:json)?", "", raw).replace("```", "").strip()

            try:
                match = re.search(r'\{.*\}', raw, re.DOTALL)
                if not match:
                    continue
                res = json.loads(match.group(0))

                to_remove = [r.strip().lower() for r in res.get("to_remove", [])]
                to_add    = res.get("to_add", [])

                if not to_remove and not to_add:
                    continue

                print(f"[ConsolidationAgent] {cat}: removing {len(to_remove)}, adding {len(to_add)}")

                # Filter out items to remove (by normalized text match)
                kept = []
                for item in memories[cat]:
                    txt = (item.get("text") or item.get("content", "") if isinstance(item, dict) else str(item)).strip().lower()
                    if txt not in to_remove:
                        kept.append(item)

                # Add merged entries
                from datetime import datetime
                for new_text in to_add:
                    kept.append({
                        "text": new_text,
                        "added_at": datetime.utcnow().isoformat(),
                        "importance": 3,
                        "access_count": 0
                    })

                memories[cat] = kept
                changed = True

            except Exception as e:
                print(f"[ConsolidationAgent] Error processing {cat}: {e}")

        if changed:
            self.store.save_memory(memories)
            print("[ConsolidationAgent] Consolidation complete — memory optimized.")
        else:
            print("[ConsolidationAgent] Nothing to consolidate.")


def run_consolidation(memory_store):
    """Entry point for scheduler."""
    agent = ConsolidationAgent(memory_store)
    agent.consolidate()
