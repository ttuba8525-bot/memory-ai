import json
import re
from utils.llm import generate_response

def _get_text(entry):
    """Support both legacy plain strings and dict format."""
    if isinstance(entry, dict):
        return entry.get("text") or entry.get("content", "")
    return str(entry)

def resolve_memory_conflicts(new_facts, new_prefs, memory_store, new_goals=None):
    """
    Conflict Agent: Compares new memory against existing memory.
    If contradictions are found, the NEW memory takes precedence.
    Returns: (new_facts, new_prefs, new_goals, conflict_description)
    conflict_description is a human-readable string if a conflict was detected, else None.
    """
    if new_goals is None:
        new_goals = []

    mem = memory_store.load_memory()
    existing_facts = mem.get("facts", [])
    existing_prefs = mem.get("preferences", [])

    if not existing_facts and not existing_prefs:
        return new_facts, new_prefs, new_goals, None

    if not new_facts and not new_prefs and not new_goals:
        return [], [], [], None

    # Extract plain text for prompt
    ef_texts = [_get_text(e) for e in existing_facts]
    ep_texts = [_get_text(e) for e in existing_prefs]

    existing_memory_str = ""
    if ef_texts:
        existing_memory_str += "Existing Facts:\n" + "\n".join(f"  - {t}" for t in ef_texts)
    if ep_texts:
        existing_memory_str += "\n\nExisting Preferences:\n" + "\n".join(f"  - {t}" for t in ep_texts)

    new_memory_str = ""
    if new_facts:
        new_memory_str += "New Facts:\n" + "\n".join(f"  - {t}" for t in new_facts)
    if new_prefs:
        new_memory_str += "\n\nNew Preferences:\n" + "\n".join(f"  - {t}" for t in new_prefs)
    if new_goals:
        new_memory_str += "\n\nNew Goals:\n" + "\n".join(f"  - {t}" for t in new_goals)

    prompt = f"""You are a memory conflict resolver for a personal AI assistant.
Find DIRECT contradictions between existing and new memory.
A contradiction example: "User's favorite color is blue" vs "User's favorite color is red".
Only flag it as a conflict if it is a clear contradiction, NOT just an update or addition.

Return ONLY valid JSON (no markdown, no code blocks):
{{
  "conflicts_found": true or false,
  "conflict_description": "One-sentence human-readable summary of what changed, e.g. 'User updated their favorite city from Pune to Bangalore.' Or null if no conflict.",
  "remove_facts": ["exact fact strings to remove from existing memory"],
  "remove_preferences": ["exact preference strings to remove from existing memory"]
}}

Existing Memory:
{existing_memory_str}

New Memory:
{new_memory_str}

Return ONLY valid JSON:"""

    messages = [{"role": "user", "content": prompt}]
    response = generate_response(messages, temp=0.1)

    # Strip markdown code blocks if present
    response = response.strip()
    if response.startswith("```"):
        response = re.sub(r"```(?:json)?", "", response).replace("```", "").strip()

    remove_facts, remove_prefs = [], []
    conflict_description = None

    try:
        data = json.loads(response)
        remove_facts = data.get("remove_facts", [])
        remove_prefs = data.get("remove_preferences", [])
        if data.get("conflicts_found") and data.get("conflict_description"):
            conflict_description = data["conflict_description"]
    except Exception:
        match = re.search(r'\{.*\}', response, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(0))
                remove_facts = data.get("remove_facts", [])
                remove_prefs = data.get("remove_preferences", [])
                if data.get("conflicts_found") and data.get("conflict_description"):
                    conflict_description = data["conflict_description"]
            except Exception:
                pass

    # Apply removals — match by partial text content (case insensitive) to be robust against LLM hallucinating exact format
    if remove_facts or remove_prefs:
        m = memory_store.load_memory()
        
        def should_keep(entry, removal_list):
            text = _get_text(entry).lower().strip()
            for r in removal_list:
                r_clean = str(r).lower().strip()
                # If the removal string is substantial (>5 chars) and is a substring of the fact, remove it.
                if len(r_clean) > 5 and (r_clean in text or text in r_clean):
                    return False
                if r_clean == text:
                    return False
            return True

        m["facts"]       = [e for e in m.get("facts", [])       if should_keep(e, remove_facts)]
        m["preferences"] = [e for e in m.get("preferences", []) if should_keep(e, remove_prefs)]
        memory_store.save_memory(m)

    return new_facts, new_prefs, new_goals, conflict_description
