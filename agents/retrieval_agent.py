from utils.llm import generate_response

def retrieve_relevant_memory(user_input, memory_store):
    """
    Retrieve facts, preferences, and goals from the memory store
    that are relevant to the user's input.
    Returns a string summarizing relevant memory context, or empty string if nothing matches.
    """
    mem = memory_store.load_memory()
    facts = mem.get("facts", [])
    prefs = mem.get("preferences", [])
    goals = mem.get("goals", [])

    if not facts and not prefs and not goals:
        return ""

    def _t(e):
        if isinstance(e, dict):
            return e.get("text") or e.get("content", "")
        return str(e)

    # Format memory into a string for the LLM
    memory_context = ""
    if facts:
        memory_context += "Facts:\n" + "".join(f"- {_t(f)}\n" for f in facts)
    if prefs:
        memory_context += "\nPreferences:\n" + "".join(f"- {_t(p)}\n" for p in prefs)
    if goals:
        memory_context += "\nGoals:\n" + "".join(f"- {_t(g)}\n" for g in goals)

    prompt = f"""Given the user's new message, select the most relevant facts, preferences,
and goals from the stored memory below.
Return only the relevant ones as a concise summary.
If nothing is directly relevant to the user's message, reply exactly with the word "None".

Stored Memory:
{memory_context}

User message: {user_input}
"""

    messages = [{"role": "user", "content": prompt}]
    relevance_summary = generate_response(messages, temp=0.1)

    if relevance_summary.strip().lower() == "none":
        return ""

    return relevance_summary
