import json
from utils.llm import generate_response

def extract_memory(user_input, ai_response):
    """
    Extract facts and preferences from the conversation.
    Returns a tuple: (list of facts, list of preferences)
    """
    prompt = f"""
    Analyze the following conversation and extract any new, permanent facts about the user or their preferences.
    Return ONLY a JSON object with two keys: "facts" (list of strings) and "preferences" (list of strings).
    If there is nothing to store, return {{"facts": [], "preferences": []}}.
    Do not include conversational filler, greetings, or transient states like "I am tired right now".

    User: {user_input}
    AI: {ai_response}
    """
    messages = [{"role": "user", "content": prompt}]
    response = generate_response(messages, temp=0.1)
    
    try:
        data = json.loads(response)
        return data.get("facts", []), data.get("preferences", [])
    except Exception:
        # Fallback regex to parse JSON in case there is markdown or text around it
        import re
        match = re.search(r'\{.*\}', response, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(0))
                return data.get("facts", []), data.get("preferences", [])
            except:
                pass
    return [], []
