import os
import requests
from dotenv import load_dotenv

def generate_response(messages, temp=0.7):
    """
    Generate a response from the OpenRouter API.
    messages: list of dicts with 'role' and 'content'
    """
    load_dotenv(override=True)
    api_key = os.getenv("OPENROUTER_API_KEY")
    
    if not api_key:
        print("[LLM Error] OPENROUTER_API_KEY not found in environment.")
        return "I'm sorry, my core brain is offline without an API key."

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}"
            },
            json={
                "model": "meta-llama/llama-3-70b-instruct",
                "messages": messages,
                "temperature": temp,
            }
        )
        if response.status_code != 200:
            print(f"[LLM Error] OpenRouter API returned {response.status_code}: {response.text}")
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"[LLM Exception] Error calling OpenRouter API: {e}")
        return "I'm sorry, I'm having trouble connecting to my brain right now."
