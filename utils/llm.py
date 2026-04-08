import os
import requests
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

def generate_response(messages, temp=0.7):
    """
    Generate a response from the OpenRouter API.
    messages: list of dicts with 'role' and 'content'
    """
    if not OPENROUTER_API_KEY:
        return "Error: OPENROUTER_API_KEY not found in environment."

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}"
            },
            json={
                "model": "meta-llama/llama-3-70b-instruct",
                "messages": messages,
                "temperature": temp,
            }
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"Error calling OpenRouter API: {e}")
        return "I'm sorry, I'm having trouble connecting to my brain right now."
