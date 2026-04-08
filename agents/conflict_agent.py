from utils.llm import generate_response
import json
import re

def resolve_memory_conflicts(new_facts, new_prefs, memory_store):
    """
    Check if the new memory conflicts with existing memory.
    If so, we assume the latest memory (user's new statement) takes precedence.
    Removes conflicting outdated memories from the store.
    """
    mem = memory_store.load_memory()
    existing_facts = mem.get("facts", [])
    existing_prefs = mem.get("preferences", [])
    
    if not existing_facts and not existing_prefs:
        return new_facts, new_prefs
        
    if not new_facts and not new_prefs:
        return [], []
    
    existing_memory_str = "Existing Facts:\n" + "\n".join(existing_facts) + "\n\nExisting Preferences:\n" + "\n".join(existing_prefs)
    new_memory_str = "New Facts:\n" + "\n".join(new_facts) + "\n\nNew Preferences:\n" + "\n".join(new_prefs)
    
    prompt = f"""
    You are managing a user's memory. Determine if there are any direct contradictions between the Existing Memory and the New Memory.
    For example, if Existing says "User's favorite color is blue" and New says "User's favorite color is red".
    If there is a contradiction, the New Memory takes precedence.
    Return ONLY a JSON object containing the lists of exact outdated strings to REMOVE from the existing memory.
    Format required: {{"remove_facts": ["exact fact string"], "remove_preferences": ["exact pref string"]}}
    If there are no conflicts, return {{"remove_facts": [], "remove_preferences": []}}.

    Existing Memory:
    {existing_memory_str}
    
    New Memory:
    {new_memory_str}
    """
    
    messages = [{"role": "user", "content": prompt}]
    response = generate_response(messages, temp=0.1)
    
    remove_facts, remove_prefs = [], []
    
    try:
        data = json.loads(response)
        remove_facts = data.get("remove_facts", [])
        remove_prefs = data.get("remove_preferences", [])
    except Exception:
        match = re.search(r'\{.*\}', response, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(0))
                remove_facts = data.get("remove_facts", [])
                remove_prefs = data.get("remove_preferences", [])
            except:
                pass

    # Clean up exact matches
    if remove_facts or remove_prefs:
        updated = False
        m = memory_store.load_memory()
        for fact in remove_facts:
            if fact in m.get("facts", []):
                m["facts"].remove(fact)
                updated = True
        for pref in remove_prefs:
            if pref in m.get("preferences", []):
                m["preferences"].remove(pref)
                updated = True
        if updated:
            memory_store.save_memory(m)
            
    return new_facts, new_prefs
