from flask import Blueprint, request, jsonify
from utils.llm import generate_response
from memory.store import MemoryStore
from agents.memory_agent import extract_memory
from agents.retrieval_agent import retrieve_relevant_memory
from agents.conflict_agent import resolve_memory_conflicts

chat_bp = Blueprint('chat', __name__)
memory_store = MemoryStore("memory.json")

# Simple conversation history for the session
session_history = []

@chat_bp.route("/api/chat", methods=["POST"])
def chat():
    data = request.json
    user_input = data.get("message")
    
    if not user_input:
        return jsonify({"error": "Message is required"}), 400

    # 1. Retrieve relevant memory
    relevant_memory = retrieve_relevant_memory(user_input, memory_store)
    
    # 2. Construct LLM prompt with history & memory
    system_prompt = "You are an intelligent AI assistant with a persistent memory of the user."
    if relevant_memory:
        system_prompt += f"\nHere is relevant information from your past interactions with this user:\n{relevant_memory}"
        
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(session_history)
    messages.append({"role": "user", "content": user_input})
    
    # Generate Response
    ai_response = generate_response(messages)
    
    # Update Session History
    session_history.append({"role": "user", "content": user_input})
    session_history.append({"role": "assistant", "content": ai_response})
    
    # 3. Extract New Memory
    new_facts, new_prefs = extract_memory(user_input, ai_response)
    
    # 4. Resolve Conflicts and Store
    if new_facts or new_prefs:
        resolved_facts, resolved_prefs = resolve_memory_conflicts(new_facts, new_prefs, memory_store)
        memory_store.update_memory(resolved_facts, resolved_prefs)
        
    return jsonify({
        "response": ai_response,
        "extracted_facts": new_facts,
        "extracted_prefs": new_prefs,
        "relevant_memory": relevant_memory
    })
