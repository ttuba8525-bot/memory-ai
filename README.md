# 🧠 DejaVu AI — Agentic Memory Assistant

> **"Remember everything. Understand deeply. Never repeat yourself."**

DejaVu AI is a full-stack, agentic personal AI assistant that **remembers who you are** across conversations. Unlike typical AI chatbots that forget everything once the tab closes, DejaVu builds and maintains a living memory of your facts, preferences, and goals — and uses that memory to make every response feel deeply personal.

---

## ✨ Features

| Feature | Description |
|---|---|
| 🧠 **Persistent Memory** | Remembers facts, preferences, and goals per user across sessions |
| 🤖 **4 Specialized Agents** | Memory extraction, retrieval, conflict resolution, and consolidation |
| 🎭 **Persona System** | 4 AI personalities: Friend, Tutor, Coach, Professional |
| ⚔️ **Conflict Resolution** | Detects and resolves contradictory memories automatically |
| 📉 **Memory Decay Engine** | Importance scores decay over time unless memories are accessed |
| 🔄 **Nightly Consolidation** | LLM-driven agent merges redundant memories daily |
| ⏰ **Email Reminders** | Scheduled email notifications for user-set reminders |
| 📊 **Insights Dashboard** | Visual analytics of memory growth, topic clusters, and conflicts |
| 🗂️ **Memory Editor** | Full CRUD on facts, preferences, and goals from the UI |
| 📄 **Legal Document Analyzer** | Paste or upload a PDF contract for AI-powered risk extraction |
| 📤 **Chat Export** | Download full conversation history as a Markdown file |
| 🔐 **Auth System** | Register/Login/Guest access with email verification |
| 💬 **Context-Aware Suggestions** | Prompts are generated from your existing memory |
| 📁 **Chat Archive** | All conversations are archived server-side, linked to your account |

---

## 🏗️ Project Structure

```
DejaVu-AI/
│
├── app.py                    # Flask app entry point + background scheduler
├── models.py                 # SQLAlchemy User model
├── personas.py               # Persona definitions and system prompt library
├── requirements.txt          # Python dependencies
├── .env                      # API keys and SMTP credentials (not committed)
├── .env.example              # Template for env vars
│
├── routes/
│   ├── auth.py               # Auth endpoints: register, login, guest, verify, logout
│   └── chat.py               # All API endpoints: chat, memory, reminders, legal, exports
│
├── agents/
│   ├── memory_agent.py       # Extracts facts/prefs/goals from conversation using LLM
│   ├── retrieval_agent.py    # Filters relevant memory for each user message
│   ├── conflict_agent.py     # Detects contradictions, removes stale memories
│   └── consolidation_agent.py# Nightly merger of duplicate/similar memories
│
├── memory/
│   ├── store.py              # MemoryStore class: JSON-backed per-user memory with backup/repair
│   ├── decay.py              # MemoryDecay engine: importance decay by day + access bonus
│   ├── user_<id>.json        # Per-user memory file (facts/prefs/goals)
│   ├── conflicts_<id>.json   # Conflict log per user
│   ├── reminders_<id>.json   # Reminder list per user
│   └── chats_<id>.json       # Archived chat history per user
│
├── utils/
│   ├── llm.py                # OpenRouter API wrapper (calls LLaMA-3 70B)
│   └── email_sender.py       # SMTP email sender for verification + reminders
│
├── templates/
│   ├── splash.html           # Landing page
│   ├── auth.html             # Login / Register / Guest UI
│   ├── index.html            # Main chat interface
│   ├── memory_editor.html    # Memory CRUD editor
│   ├── insights.html         # Analytics dashboard
│   ├── profile.html          # User profile + persona switcher
│   ├── reminders.html        # Reminder manager
│   └── legal.html            # Legal document analyzer
│
└── static/
    ├── script.js             # Frontend logic (chat, agent trace, memory, etc.)
    └── style.css             # Global CSS and theming
```

---

## ⚙️ How It Works — Full System Architecture

### 1. Request-Response Flow

Every time you send a message, the following 6-step pipeline runs on the backend:

```
User Message (browser)
        │
        ▼
[POST /api/chat]  ──────────────────────────────────────────────────────────
        │
        ├─ Step 1: RETRIEVAL AGENT
        │         Scans the user's memory store and asks the LLM to select
        │         the most relevant facts/prefs/goals for this message.
        │
        ├─ Step 2: PROMPT BUILDER
        │         Selects the persona (Friend / Tutor / Coach / Professional)
        │         and prepends relevant memory context to the system prompt.
        │
        ├─ Step 3: LLM CALL (OpenRouter → LLaMA-3 70B)
        │         Sends [system prompt + session history + user message]
        │         to the LLM and gets a response.
        │
        ├─ Step 4: HISTORY UPDATE + ARCHIVE
        │         Appends message/response to in-memory session history.
        │         Saves full exchange to chats_<id>.json (persistent archive).
        │
        ├─ Step 5: MEMORY AGENT
        │         Sends the raw conversation to the LLM again to extract
        │         new facts, preferences, and goals as structured JSON.
        │
        └─ Step 6: CONFLICT AGENT
                  Compares new memory against existing memory.
                  If contradictions exist, the old memory is removed.
                  Result is saved to user_<id>.json.
        │
        ▼
JSON Response → { response, extracted_facts, extracted_prefs, extracted_goals,
                  relevant_memory, agent_trace }
```

The `agent_trace` field is sent with every response and shows the frontend a step-by-step breakdown of what each agent did, including execution time in milliseconds.

---

### 2. Frontend ↔ Backend Connection

The frontend is **pure HTML + Vanilla JS** served by Flask's Jinja2 templating engine. Pages are rendered server-side, but all interactions after page load are handled via **AJAX calls to REST API endpoints**.

```
Browser (HTML + JS)              Flask Backend (Python)
─────────────────────────        ──────────────────────────────
Sends: POST /api/chat  ────────► chat_bp.chat()
  { message: "..." }                │ calls agents → LLM → saves memory
                                    │
Receives: JSON ◄───────────────── returns response + trace + memory data

Sends: GET /api/memory ────────► get_store().load_memory()
Receives: { facts, prefs, goals }

Sends: DELETE /api/memory/fact/2  ► delete_fact(idx)
Sends: PUT /api/memory/pref/1     ► update_pref(idx)

Sends: POST /api/reminder ─────► add_reminder()
Sends: GET /api/reminder/pending ► pending_reminders()

Sends: POST /api/persona ──────► set_persona()  → saved to SQLite DB

Sends: POST /api/legal/analyze ► legal_analyze() → LLM structured extraction
Sends: POST /api/legal/upload-pdf ► pdfplumber text extraction
```

**Session state** (chat history within a tab session) is stored in a Python `dict` (`_session_history`) keyed by `user.id`. This resets on server restart. Permanent data (facts, preferences, goals, reminders, archives) is stored in flat JSON files.

**Authentication state** is managed by `flask-login` using server-side sessions (cookie-based). All protected routes require `@login_required`.

---

### 3. LLM Integration — OpenRouter API

All AI intelligence flows through a single utility function in `utils/llm.py`:

```python
def generate_response(messages, temp=0.7):
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
        json={
            "model": "meta-llama/llama-3-70b-instruct",
            "messages": messages,   # [{ role, content }, ...]
            "temperature": temp,
        }
    )
    return response.json()["choices"][0]["message"]["content"]
```

**Why OpenRouter?** OpenRouter is an API gateway that provides access to many open and closed LLMs through a single endpoint. DejaVu uses **LLaMA-3 70B Instruct** for its:
- Strong instruction-following (agents need structured JSON output)
- Cost efficiency vs. GPT-4 class models
- Ability to run long context windows (full memory + history)

The LLM is called **up to 3 times per user message**:
| Call # | Purpose | Temp |
|---|---|---|
| 1 | Retrieval Agent — filter relevant memory | 0.1 (deterministic) |
| 2 | Main chat response generation | 0.7 (creative) |
| 3 | Memory Agent — extract new facts/prefs/goals | 0.1 (deterministic) |
| 4 | Conflict Agent — find contradictions (if new memory exists) | 0.1 (deterministic) |

Low temperature (0.1) is used for agents that must output valid, parseable JSON.

---

## 🤖 Agents — Deep Dive

### Agent 1: Memory Agent (`agents/memory_agent.py`)

**Purpose:** Automatically extracts permanent information from every conversation.

**How it's created:** A structured prompt is constructed with the user message and AI response, then sent to the LLM with an instruction to return only a specific JSON shape:

```python
prompt = """
Analyze the following conversation and extract any new, permanent information.
Return ONLY a JSON object:
- "facts": concrete things about the user (name, job, location, hobbies)
- "preferences": likes, dislikes, tastes, habits
- "goals": things the user wants to achieve

Rules:
- Only store permanent/semi-permanent things.
- Skip transient states like "I am tired right now".
- Return ONLY valid JSON: {"facts": [], "preferences": [], "goals": []}

User: {user_input}
AI: {ai_response}
"""
```

**Output:** A tuple `(facts_list, preferences_list, goals_list)` which is then passed to the Conflict Agent and stored.

---

### Agent 2: Retrieval Agent (`agents/retrieval_agent.py`)

**Purpose:** Prevents the LLM from being overwhelmed with your entire memory. Only the *relevant* subset is injected into the prompt.

**How it works:**
1. Loads all facts, preferences, and goals from `MemoryStore`
2. Formats them as a plain-text block
3. Sends them + the user's new message to the LLM
4. The LLM returns only the entries that are actually relevant
5. If nothing is relevant, it returns the exact string `"None"` (checked with `== "none"` after lowercasing)

**Why this matters:** Without retrieval filtering, a user with 200 stored memories would blow the context window and cause irrelevant information to dilute the response quality.

---

### Agent 3: Conflict Agent (`agents/conflict_agent.py`)

**Purpose:** Ensures memory stays accurate. When the user contradicts a past belief, the old memory is automatically removed and replaced.

**How it works:**
1. Receives the new facts/prefs about to be stored
2. Loads all existing facts/prefs from the memory store
3. Builds a prompt asking the LLM to identify **direct contradictions only** (not just additions)
4. LLM returns a JSON object:

```json
{
  "conflicts_found": true,
  "conflict_description": "User updated their favorite color from blue to red.",
  "remove_facts": ["User's favorite color is blue"],
  "remove_preferences": []
}
```

5. The agent removes matched entries from the store using **fuzzy substring matching** (robust against LLM paraphrasing)
6. A conflict log entry is saved to `conflicts_<id>.json` for display in the Insights dashboard

**Key design decision:** New memory always wins. The conflict agent prioritizes recency — whatever the user just said overrides what they said before.

---

### Agent 4: Consolidation Agent (`agents/consolidation_agent.py`)

**Purpose:** Runs nightly (scheduled at 03:00 via APScheduler) to clean up the memory store. Merges duplicate, redundant, or slightly different phrasings of the same memory into one clean entry.

**How it works:**
1. For each category (facts, preferences, goals), it sends the full content list to the LLM
2. The LLM identifies items that say the "same thing in different ways" and suggests:
   - `to_remove`: exact strings to delete
   - `to_add`: new merged, well-written versions
3. The agent applies the changes to the memory store and saves

**Example:** Two entries — `"User likes hiking"` and `"User enjoys outdoor hiking trails"` — would be merged into `"User enjoys hiking and outdoor trails"`.

---

## 🗄️ Memory Storage System

### MemoryStore (`memory/store.py`)

Each user has a dedicated JSON memory file at `memory/user_<id>.json`:

```json
{
  "facts": [
    {
      "text": "User's name is Alex",
      "added_at": "2026-04-09T05:30:00",
      "importance": 4,
      "access_count": 3
    }
  ],
  "preferences": [...],
  "goals": [...]
}
```

**Fields per memory entry:**
| Field | Description |
|---|---|
| `text` | The memory content |
| `added_at` | ISO timestamp of when it was created |
| `importance` | Score 1–5 (starts at 3, decays over time) |
| `access_count` | Increments each time retrieval agent uses this memory |

**Backup & Auto-repair:** Every successful `load_memory()` call creates a `.backup` copy. If the main file becomes corrupted (invalid JSON, empty file), the system automatically restores from backup.

### Memory Decay Engine (`memory/decay.py`)

Runs daily at 02:00 via APScheduler. Applies importance decay so that old, unaccessed memories gradually lose weight.

**Decay formula:**
```
importance = base × (1 - decay_rate)^days_since_added + access_bonus
```
- `decay_rate` = 4% per day
- `access_bonus` = 5% per retrieval hit (capped at +30%)
- Importance is clipped to range [1, 5]

This means a fact accessed often stays high-importance, while forgotten facts fade naturally.

---

## 🎭 Persona System

The persona affects the **system prompt** prepended to every chat request. Users can switch persona at any time from the Profile page. The selection is persisted to the SQLite database.

| Persona | Label | Behaviour |
|---|---|---|
| `friend` | Casual Friend 🤝 | Warm, conversational, light humour, concise |
| `tutor` | Patient Tutor 📚 | Step-by-step explanations, analogies, celebrates progress |
| `coach` | Life Coach 🏆 | Goal-oriented, motivating, action-focused, accountability |
| `formal` | Professional 💼 | Precise formal language, structured, no casual expressions |

**How it flows into the LLM:**
```python
system_prompt = get_persona_prompt(persona_key)          # Personality base
if relevant_memory:
    system_prompt += f"\n\nRelevant memory:\n{relevant_memory}"  # Memory context
messages = [{"role": "system", "content": system_prompt}, ...history, user_message]
```

---

## 🔐 Authentication System

**Routes:** `routes/auth.py`

| Endpoint | Method | Description |
|---|---|---|
| `/auth/register` | POST | Register with username + email + password |
| `/auth/login` | POST | Login with email + password |
| `/auth/guest` | POST | Create a temporary guest account (auto-generated UUID username) |
| `/auth/verify/<token>` | GET | Email verification link handler |
| `/auth/logout` | GET | Logs out and redirects to auth page |
| `/auth/me` | GET | Returns current user info as JSON |

**User model** (`models.py`) uses:
- `werkzeug.security` for bcrypt password hashing
- `flask-login` for session management
- Per-user helper methods: `memory_path()`, `conflicts_path()`, `reminders_path()`, `chats_path()`

---

## ⏰ Background Scheduler

`APScheduler` runs a `BackgroundScheduler` daemon with 3 recurring jobs:

| Job | Schedule | Function |
|---|---|---|
| Memory Decay | Daily @ 02:00 | Applies importance decay to all user memory files |
| Consolidation | Daily @ 03:00 | LLM-merges redundant memories for all users |
| Reminder Check | Every 1 minute | Scans reminders, sends due ones via SMTP email |

All jobs iterate over all `memory/user_*.json` files to process every registered user.

---

## 📡 API Reference

### Chat
| Endpoint | Method | Payload | Response |
|---|---|---|---|
| `/api/chat` | POST | `{ message }` | `{ response, extracted_facts, extracted_prefs, extracted_goals, relevant_memory, agent_trace }` |
| `/api/export` | GET | — | Markdown file download |

### Memory
| Endpoint | Method | Description |
|---|---|---|
| `/api/memory` | GET | Full memory dump (facts, prefs, goals) |
| `/api/memory/search?q=...` | GET | Substring search across all memory |
| `/api/memory/fact/<idx>` | PUT / DELETE | Edit or delete a fact by index |
| `/api/memory/pref/<idx>` | PUT / DELETE | Edit or delete a preference by index |
| `/api/memory/goal/<idx>` | PUT / DELETE | Edit or delete a goal by index |
| `/api/memory-stats` | GET | Analytics: totals, growth timeline, topic clusters, conflicts |

### Persona & Suggestions
| Endpoint | Method | Payload |
|---|---|---|
| `/api/persona` | POST | `{ persona: "friend" \| "tutor" \| "coach" \| "formal" }` |
| `/api/suggestions` | GET | 3 context-aware prompt suggestions from memory |

### Reminders
| Endpoint | Method | Payload |
|---|---|---|
| `/api/reminder` | POST | `{ text, remind_at: "<ISO datetime>" }` |
| `/api/reminder` | GET | All reminders for current user |
| `/api/reminder/pending` | GET | Returns due reminders and marks them done |
| `/api/reminder/<id>` | DELETE | Delete a reminder by ID |

### Legal Analyzer
| Endpoint | Method | Payload |
|---|---|---|
| `/api/legal/analyze` | POST | `{ text: "<document text>" }` |
| `/api/legal/upload-pdf` | POST | `multipart/form-data` with PDF file |

### Chats
| Endpoint | Method | Description |
|---|---|---|
| `/api/chats` | GET | Full archived chat history for current user |

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- An [OpenRouter](https://openrouter.ai) API key
- (Optional) SMTP credentials for email reminders

### Installation

```bash
# Clone the repository
git clone https://github.com/your-username/DejaVu-AI.git
cd DejaVu-AI

# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate       # Windows
# source venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt
```

### Environment Setup

Create a `.env` file in the project root (see `.env.example`):

```env
OPENROUTER_API_KEY=sk-or-...your-key-here...
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@gmail.com
SMTP_PASS=your-app-password
```

### Run the App

```bash
python app.py
```

Navigate to **http://localhost:5000** in your browser.

---

## 🗺️ Pages

| URL | Template | Description |
|---|---|---|
| `/` | `splash.html` | Landing page |
| `/auth` | `auth.html` | Login / Register / Guest |
| `/chat` | `index.html` | Main chat interface with agent trace |
| `/memory` | `memory_editor.html` | View, edit, delete all memories |
| `/insights` | `insights.html` | Analytics, topic clusters, conflict log |
| `/profile` | `profile.html` | Persona switcher, account info |
| `/reminders` | `reminders.html` | Set and manage email reminders |
| `/legal` | `legal.html` | AI-powered legal document analyzer |

---

## 🔧 Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3, Flask, Flask-Login, Flask-SQLAlchemy |
| **Database** | SQLite (via SQLAlchemy) — stores user accounts |
| **Memory Storage** | Flat JSON files per user (no DB overhead) |
| **LLM Provider** | OpenRouter API → Meta LLaMA-3 70B Instruct |
| **Scheduler** | APScheduler (BackgroundScheduler, daemon mode) |
| **Email** | Python `smtplib` + `email.mime` |
| **PDF Parsing** | `pdfplumber` |
| **Frontend** | HTML5, Vanilla JS (fetch API), Vanilla CSS |
| **Auth** | Flask-Login + Werkzeug bcrypt hashing |

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

*Built with ❤️ and a lot of memory.*
