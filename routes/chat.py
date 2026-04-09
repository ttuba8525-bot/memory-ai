import json, os, re, time
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, make_response
from flask_login import current_user, login_required
from memory.store import MemoryStore
from agents.memory_agent import extract_memory
from agents.retrieval_agent import retrieve_relevant_memory
from agents.conflict_agent import resolve_memory_conflicts
from utils.llm import generate_response
from personas import get_persona_prompt, PERSONAS

chat_bp = Blueprint('chat', __name__)

# ── per-request helpers ──────────────────────────────────────────────────────

def get_store():
    """Return a MemoryStore scoped to the current user (or anonymous default)."""
    if current_user.is_authenticated:
        path = current_user.memory_path()
    else:
        path = "memory/user_default.json"
    return MemoryStore(path)


def load_conflicts():
    if current_user.is_authenticated:
        path = current_user.conflicts_path()
    else:
        path = "memory/conflicts_default.json"
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except Exception:
        return []


def save_conflict(entry: dict):
    if current_user.is_authenticated:
        path = current_user.conflicts_path()
    else:
        path = "memory/conflicts_default.json"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = load_conflicts()
    data.append(entry)
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)


def load_reminders():
    if not current_user.is_authenticated:
        return []
    try:
        with open(current_user.reminders_path(), 'r') as f:
            return json.load(f)
    except Exception:
        return []


def save_reminders(data):
    path = current_user.reminders_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)

def load_archived_chats():
    if not current_user.is_authenticated:
        return []
    try:
        with open(current_user.chats_path(), 'r') as f:
            return json.load(f)
    except Exception:
        return []

def save_archived_chats(data):
    if not current_user.is_authenticated:
        return
    path = current_user.chats_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)



# Per-request session history (resets on restart; good enough for demo)
_session_history = {}

def get_history():
    uid = current_user.id if current_user.is_authenticated else 0
    return _session_history.setdefault(uid, [])


_session_stats = {}

def get_stats():
    uid = current_user.id if current_user.is_authenticated else 0
    return _session_stats.setdefault(uid, {
        "turns": 0, "facts_this_session": 0, "prefs_this_session": 0
    })


# ── /api/chat ────────────────────────────────────────────────────────────────

@chat_bp.route("/api/chat", methods=["POST"])
def chat():
    data = request.json
    user_input = data.get("message", "").strip()
    if not user_input:
        return jsonify({"error": "Message is required"}), 400

    trace = []
    store = get_store()
    history = get_history()
    stats = get_stats()

    # 1. Retrieve memory
    t0 = time.time()
    relevant_memory = retrieve_relevant_memory(user_input, store)
    trace.append({"step": "Memory Retrieval", "ms": round((time.time()-t0)*1000),
                  "result": relevant_memory or "Nothing relevant found"})

    # 2. Build prompt with persona
    persona_key = current_user.persona if current_user.is_authenticated else "friend"
    system_prompt = get_persona_prompt(persona_key)
    if relevant_memory:
        system_prompt += f"\n\nRelevant memory:\n{relevant_memory}"

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_input})
    trace.append({"step": "Prompt Built", "ms": 0,
                  "result": f"Persona={persona_key}, context_msgs={len(messages)}"})

    # 3. LLM
    t0 = time.time()
    ai_response = generate_response(messages)
    trace.append({"step": "LLM Response", "ms": round((time.time()-t0)*1000),
                  "result": ai_response[:120] + ("…" if len(ai_response)>120 else "")})

    # 4. Update history
    history.append({"role": "user",      "content": user_input})
    history.append({"role": "assistant", "content": ai_response})
    stats["turns"] += 1

    archive = load_archived_chats()
    archive.append({
        "timestamp": datetime.utcnow().isoformat(),
        "user_input": user_input,
        "ai_response": ai_response,
        "persona": persona_key
    })
    save_archived_chats(archive)

    # 5. Extract memory (facts, prefs, goals)
    t0 = time.time()
    new_facts, new_prefs, new_goals = extract_memory(user_input, ai_response)
    trace.append({"step": "Memory Extraction", "ms": round((time.time()-t0)*1000),
                  "result": f"facts={new_facts}, prefs={new_prefs}, goals={new_goals}"})

    # 6. Resolve conflicts & store
    if new_facts or new_prefs or new_goals:
        t0 = time.time()
        resolved_facts, resolved_prefs, resolved_goals, conflict_desc = resolve_memory_conflicts(
            new_facts, new_prefs, store, new_goals=new_goals
        )
        elapsed = round((time.time()-t0)*1000)

        removed = [f for f in new_facts if f not in resolved_facts] + \
                  [p for p in new_prefs  if p not in resolved_prefs]
        if removed or conflict_desc:
            save_conflict({
                "ts": datetime.utcnow().isoformat(),
                "removed": removed,
                "description": conflict_desc or "",
                "kept_facts": resolved_facts,
                "kept_prefs": resolved_prefs
            })

        store.update_memory(resolved_facts, resolved_prefs, resolved_goals)
        stats["facts_this_session"] += len(new_facts)
        stats["prefs_this_session"] += len(new_prefs)
        trace.append({"step": "Conflict Resolution", "ms": elapsed,
                      "result": conflict_desc or (f"removed={removed}" if removed else "no conflicts")})

    return jsonify({
        "response":       ai_response,
        "extracted_facts": new_facts,
        "extracted_prefs": new_prefs,
        "extracted_goals": new_goals,
        "relevant_memory": relevant_memory,
        "agent_trace":    trace
    })


# ── /api/memory/* ─────────────────────────────────────────────────────────────

@chat_bp.route("/api/memory", methods=["GET"])
def get_memory():
    return jsonify(get_store().load_memory())


@chat_bp.route("/api/memory/search")
def search_memory():
    q = request.args.get("q", "")
    return jsonify(get_store().search_memory(q))


@chat_bp.route("/api/memory/fact/<int:idx>", methods=["PUT"])
def update_fact(idx):
    text = (request.json or {}).get("text", "").strip()
    if text:
        get_store().update_fact(idx, text)
    return jsonify({"ok": True})


@chat_bp.route("/api/memory/pref/<int:idx>", methods=["PUT"])
def update_pref(idx):
    text = (request.json or {}).get("text", "").strip()
    if text:
        get_store().update_pref(idx, text)
    return jsonify({"ok": True})


@chat_bp.route("/api/memory/fact/<int:idx>", methods=["DELETE"])
def delete_fact(idx):
    get_store().delete_fact(idx)
    return jsonify({"ok": True})


@chat_bp.route("/api/memory/pref/<int:idx>", methods=["DELETE"])
def delete_pref(idx):
    get_store().delete_pref(idx)
    return jsonify({"ok": True})


@chat_bp.route("/api/memory/goal/<int:idx>", methods=["PUT"])
def update_goal(idx):
    text = (request.json or {}).get("text", "").strip()
    if text:
        get_store().update_goal(idx, text)
    return jsonify({"ok": True})


@chat_bp.route("/api/memory/goal/<int:idx>", methods=["DELETE"])
def delete_goal(idx):
    get_store().delete_goal(idx)
    return jsonify({"ok": True})


# ── /api/memory-stats ─────────────────────────────────────────────────────────

@chat_bp.route("/api/memory-stats", methods=["GET"])
def memory_stats():
    mem = get_store().load_memory()
    facts = mem.get("facts", [])
    prefs = mem.get("preferences", [])
    stats = get_stats()

    def get_text(e):
        if isinstance(e, dict):
            return str(e.get("text") or e.get("content") or "")
        return str(e)

    def get_date(e):
        if isinstance(e, dict) and "added_at" in e:
            return e["added_at"][:10]
        return datetime.utcnow().strftime("%Y-%m-%d")

    # Growth by day
    from collections import Counter
    all_entries = facts + prefs
    growth = Counter(get_date(e) for e in all_entries)
    growth_sorted = sorted(growth.items())

    # Topic clusters — top 20 words from fact texts
    stop = {"i","a","an","the","is","was","are","were","and","or","but","to",
            "of","in","on","at","for","with","that","this","it","my","me","we",
            "he","she","they","have","has","had","not","be","been","being","am"}
    words = []
    for e in facts + prefs:
        txt = get_text(e).lower()
        words.extend(w for w in re.findall(r'\b[a-z]{3,}\b', txt) if w not in stop)
    topic_freq = sorted(Counter(words).items(), key=lambda x: -x[1])[:20]

    # recent 5
    def fmt(e):
        return {"text": get_text(e),
                "added_at": e.get("added_at","") if isinstance(e, dict) else "",
                "importance": e.get("importance", 3) if isinstance(e, dict) else 3}

    return jsonify({
        "total_facts": len(facts),
        "total_preferences": len(prefs),
        "total_memories": len(facts) + len(prefs),
        "session_turns": stats["turns"],
        "facts_this_session": stats["facts_this_session"],
        "prefs_this_session": stats["prefs_this_session"],
        "recent_facts": [fmt(e) for e in facts[-5:]],
        "recent_prefs": [fmt(e) for e in prefs[-5:]],
        "growth_by_day": growth_sorted,
        "topic_clusters": topic_freq,
        "recent_conflicts": load_conflicts()[-5:]
    })


# ── /api/export ───────────────────────────────────────────────────────────────

@chat_bp.route("/api/export")
def export_chat():
    history = get_history()
    lines = [f"# DejaVu.ai — Conversation Export\n",
             f"*Exported: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}*\n\n---\n"]
    for msg in history:
        role = "**You**" if msg["role"] == "user" else "**DejaVu**"
        lines.append(f"{role}: {msg['content']}\n\n")
    md = "".join(lines)
    resp = make_response(md)
    resp.headers["Content-Type"] = "text/markdown"
    resp.headers["Content-Disposition"] = "attachment; filename=dejavu_conversation.md"
    return resp


# ── /api/persona ──────────────────────────────────────────────────────────────

@chat_bp.route("/api/persona", methods=["POST"])
def set_persona():
    persona = (request.json or {}).get("persona", "friend")
    if persona not in PERSONAS:
        return jsonify({"error": "Unknown persona"}), 400
    if current_user.is_authenticated:
        from models import db
        current_user.persona = persona
        db.session.commit()
    return jsonify({"ok": True, "persona": persona})


# ── /api/reminder ─────────────────────────────────────────────────────────────

@chat_bp.route("/api/reminder", methods=["POST"])
def add_reminder():
    data = request.json or {}
    text       = data.get("text", "").strip()
    remind_at  = data.get("remind_at", "")      # ISO string
    if not text or not remind_at:
        return jsonify({"error": "text and remind_at required"}), 400
    reminders = load_reminders()
    reminders.append({"id": len(reminders)+1, "text": text,
                      "remind_at": remind_at, "done": False})
    save_reminders(reminders)
    return jsonify({"ok": True})


@chat_bp.route("/api/reminder", methods=["GET"])
def get_reminders():
    return jsonify(load_reminders())


@chat_bp.route("/api/reminder/pending")
def pending_reminders():
    now = datetime.utcnow()
    due = []
    remaining = []
    changed = False
    for r in load_reminders():
        try:
            t_str = r["remind_at"].replace("Z", "+00:00").replace("+00:00", "").split(".")[0]
            t = datetime.fromisoformat(t_str)
            if not r["done"] and t <= now:
                r["done"] = True
                due.append(r)
                changed = True
            remaining.append(r)
        except Exception:
            remaining.append(r)
    if changed:
        save_reminders(remaining)
    return jsonify({"due": due})


@chat_bp.route("/api/reminder/<int:rid>", methods=["DELETE"])
def delete_reminder(rid):
    reminders = [r for r in load_reminders() if r.get("id") != rid]
    save_reminders(reminders)
    return jsonify({"ok": True})


# ── /api/legal/analyze ───────────────────────────────────────────────────────

@chat_bp.route("/api/legal/analyze", methods=["POST"])
def legal_analyze():
    text = (request.json or {}).get("text", "").strip()
    if not text:
        return jsonify({"error": "Document text required"}), 400

    prompt = [
        {"role": "system", "content": (
            "You are a legal document analysis AI. Given a legal document, extract the following "
            "and respond ONLY with valid JSON in this exact format:\n"
            '{"summary":"...","risks":["...","..."],"clauses":[{"title":"...","text":"..."}]}'
        )},
        {"role": "user", "content": f"Analyze this document:\n\n{text[:4000]}"}
    ]

    raw = generate_response(prompt)
    # Extract JSON from response
    match = re.search(r'\{.*\}', raw, re.DOTALL)
    if match:
        try:
            return jsonify(json.loads(match.group()))
        except Exception:
            pass
    return jsonify({"summary": raw, "risks": [], "clauses": []})


# ── /api/legal/upload-pdf ────────────────────────────────────────────────────

@chat_bp.route("/api/legal/upload-pdf", methods=["POST"])
def legal_upload_pdf():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    f = request.files["file"]
    if not f.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Only PDF files are supported"}), 400
    try:
        import pdfplumber, io
        pdf_bytes = io.BytesIO(f.read())
        text_parts = []
        with pdfplumber.open(pdf_bytes) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text_parts.append(t)
        full_text = "\n\n".join(text_parts).strip()
        if not full_text:
            return jsonify({"error": "Could not extract text from this PDF. It may be scanned/image-based."}), 422
        return jsonify({"text": full_text, "pages": len(pdf.pages)})
    except ImportError:
        return jsonify({"error": "pdfplumber not installed. Run: pip install pdfplumber"}), 500
    except Exception as e:
        return jsonify({"error": f"PDF parsing failed: {str(e)}"}), 500


# ── /api/suggestions & /api/chats ─────────────────────────────────────────────

@chat_bp.route("/api/suggestions", methods=["GET"])
def get_suggestions():
    store = get_store()
    mem = store.load_memory()
    facts = [f for f in mem.get("facts", []) if len(str(f.get("text", ""))) > 5]
    prefs = [p for p in mem.get("preferences", []) if len(str(p.get("text", ""))) > 5]
    goals = [g for g in mem.get("goals", []) if len(str(g.get("text", ""))) > 5]
    
    import random
    pool = []
    for f in facts:
        pool.append({"type": "fact", "text": f"Ask about my fact: {f.get('text')}"})
    for p in prefs:
        pool.append({"type": "pref", "text": f"Discuss my preference: {p.get('text')}"})
    for g in goals:
        pool.append({"type": "goal", "text": f"Review my goal: {g.get('text')}"})
    
    random.shuffle(pool)
    suggestions = pool[:3]
    return jsonify({"suggestions": [s["text"] for s in suggestions]})

@chat_bp.route("/api/chats", methods=["GET"])
@login_required
def get_archived_chats():
    return jsonify(load_archived_chats())
