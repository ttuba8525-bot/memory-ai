from utils.llm import generate_response

def retrieve_relevant_memory(user_input, memory_store):
    """
    Retrieve facts and preferences from the memory store that are relevant to the user's input.
    Returns a string summarizing relevant memory context, or empty string if nothing matches.
    """
    mem = memory_store.load_memory()
    facts = mem.get("facts", [])
    prefs = mem.get("preferences", [])
    
    if not facts and not prefs:
        return ""

    # Format the memory into a string for the LLM evaluation
    def _t(e): return e["text"] if isinstance(e, dict) else e
    memory_context = "Facts:\n"
    for f in facts:
        memory_context += f"- {_t(f)}\n"
    memory_context += "\nPreferences:\n"
    for p in prefs:
        memory_context += f"- {_t(p)}\n"
    
    prompt = f"""
    Given the user's new message, select the most relevant facts and preferences from the stored memory.
    Return only the relevant ones as a concise summary. If no facts or preferences are directly relevant to the user's message, reply exactly with the word "None".

    Stored Memory:
    {memory_context}
    
    User message: {user_input}
    """
    
    messages = [{"role": "user", "content": prompt}]
    relevance_summary = generate_response(messages, temp=0.1)
    
    if relevance_summary.strip() == "None":
        return ""
        
    return relevance_summary
