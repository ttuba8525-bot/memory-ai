import json
import re
from utils.llm import generate_response

def extract_memory(user_input, ai_response):
    """
    Extract facts, preferences, and goals from the conversation.
    Returns a tuple: (list of facts, list of preferences, list of goals)
    """
    prompt = f"""
    Analyze the following conversation and extract any new, permanent information about the user.
    Return ONLY a JSON object with three keys:
    - "facts": concrete things about the user (name, job, location, hobbies etc.)
    - "preferences": likes, dislikes, tastes, habits
    - "goals": things the user wants to achieve or is working towards

    Rules:
    - Only store permanent/semi-permanent things. Skip transient states like "I am tired right now".
    - Skip conversational filler and greetings.
    - If there is nothing to store in a category, return an empty list.
    - Return ONLY valid JSON: {{"facts": [], "preferences": [], "goals": []}}

    User: {user_input}
    AI: {ai_response}
    """
    messages = [{"role": "user", "content": prompt}]
    response = generate_response(messages, temp=0.1)

    try:
        data = json.loads(response)
        return (
            data.get("facts", []),
            data.get("preferences", []),
            data.get("goals", [])
        )
    except Exception:
        match = re.search(r'\{.*\}', response, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(0))
                return (
                    data.get("facts", []),
                    data.get("preferences", []),
                    data.get("goals", [])
                )
            except Exception:
                pass
    return [], [], []
