const chatBox = document.getElementById('chat-box');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');
const memoryLogs = document.getElementById('memory-logs');
const typingIndicator = document.getElementById('typing-indicator');
const sidebarToggle = document.getElementById('sidebar-toggle');
const sidebar = document.getElementById('sidebar');
const themeToggle = document.getElementById('theme-toggle');
const ttsToggle = document.getElementById('tts-toggle');
const voiceBtn = document.getElementById('voice-btn');

// Helper for playing sounds safely
const playSound = (freq, type, duration, vol) => {
    try {
        const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        if(!audioCtx) return;
        const oscillator = audioCtx.createOscillator();
        const gainNode = audioCtx.createGain();
        oscillator.type = type;
        oscillator.frequency.setValueAtTime(freq, audioCtx.currentTime);
        gainNode.gain.setValueAtTime(vol, audioCtx.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + duration);
        oscillator.connect(gainNode);
        gainNode.connect(audioCtx.destination);
        oscillator.start();
        oscillator.stop(audioCtx.currentTime + duration);
    } catch(e) { console.warn("Audio not supported or blocked"); }
};

const playSendSound = () => playSound(600, 'sine', 0.1, 0.1);
const playReceiveSound = () => { setTimeout(()=>playSound(800, 'sine', 0.15, 0.1), 0); setTimeout(()=>playSound(1200, 'sine', 0.2, 0.1), 100); };

// Speech Synthesis (TTS)
let isTTSAuto = false;
ttsToggle.addEventListener('click', () => {
    isTTSAuto = !isTTSAuto;
    ttsToggle.textContent = isTTSAuto ? '🔊' : '🔇';
    if (!isTTSAuto) window.speechSynthesis.cancel();
});

function speakText(text) {
    if (!isTTSAuto || !window.speechSynthesis) return;
    const cleanText = text.replace(/[*_#`]/g, '');
    const utterance = new SpeechSynthesisUtterance(cleanText);
    utterance.rate = 1.0;
    utterance.pitch = 1.0;
    window.speechSynthesis.speak(utterance);
}

// Speech Recognition (Dictation)
let recognition;
if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    
    recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        userInput.value += (userInput.value ? ' ' : '') + transcript;
        voiceBtn.style.color = '';
        voiceBtn.style.border = '';
    };
    recognition.onerror = () => { voiceBtn.style.color = ''; voiceBtn.style.border = ''; };
    recognition.onend = () => { voiceBtn.style.color = ''; voiceBtn.style.border = ''; };
}

voiceBtn.addEventListener('click', () => {
    if (!recognition) return alert('Speech Recognition is not supported in this browser.');
    voiceBtn.style.color = '#ff4d4d';
    voiceBtn.style.border = '1px solid #ff4d4d';
    recognition.start();
});

// Sidebar Toggle
sidebarToggle.addEventListener('click', () => {
    sidebar.classList.toggle('closed');
});

// Theme toggle is now handled inline in index.html via global-theme-btn

// Configure Marked.js
if (window.marked) {
    marked.setOptions({
        highlight: function(code, lang) {
            if (window.hljs) {
                const language = hljs.getLanguage(lang) ? lang : 'plaintext';
                return hljs.highlight(code, { language }).value;
            }
            return code;
        }
    });
}

function getTimestamp() {
    const now = new Date();
    return now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function copyToClipboard(text, btn) {
    navigator.clipboard.writeText(text).then(() => {
        btn.textContent = '✓';
        setTimeout(() => { btn.textContent = '⎘'; }, 1500);
    });
}

function addMessage(text, sender, skipSave = false) {
    const row = document.createElement('div');
    row.classList.add('msg-row', sender);

    const avatar = document.createElement('div');
    avatar.classList.add('avatar', sender === 'user' ? 'user-avatar' : 'ai-avatar');
    if (sender === 'ai') {
        avatar.innerHTML = '<img src="/assets/logo.png" alt="AI" style="width:100%;height:100%;border-radius:50%;object-fit:cover;">';
    } else {
        avatar.textContent = '👤';
    }

    const wrapper = document.createElement('div');
    const msgDiv = document.createElement('div');
    msgDiv.classList.add('message-content', sender);

    if (sender === 'ai' && window.marked) {
        msgDiv.innerHTML = marked.parse(text);
    } else {
        msgDiv.textContent = text;
    }

    const timeSpan = document.createElement('span');
    timeSpan.classList.add('timestamp');
    timeSpan.textContent = getTimestamp();

    if (sender === 'ai') {
        const copyBtn = document.createElement('button');
        copyBtn.className = 'copy-btn';
        copyBtn.textContent = '⎘';
        copyBtn.title = 'Copy message';
        copyBtn.onclick = () => copyToClipboard(text, copyBtn);
        timeSpan.appendChild(copyBtn);
    }

    wrapper.appendChild(msgDiv);
    wrapper.appendChild(timeSpan);
    row.appendChild(avatar);
    row.appendChild(wrapper);

    chatBox.appendChild(row);
    chatBox.scrollTop = chatBox.scrollHeight;

    // chat persistence across refresh is disabled as requested
}

// On startup, fetch suggestions instead of persisting history
window.addEventListener('DOMContentLoaded', async () => {
    const defaultMsg = document.getElementById('default-msg');
    const suggContainer = document.getElementById('suggestions-container');
    try {
        const res = await fetch('/api/suggestions');
        const data = await res.json();
        if (data.suggestions && data.suggestions.length > 0) {
            suggContainer.innerHTML = '';
            data.suggestions.forEach(s => {
                const btn = document.createElement('button');
                btn.className = 'suggestion-chip';
                btn.textContent = s;
                btn.onclick = () => {
                    userInput.value = s;
                    suggContainer.classList.add('hidden');
                    if (defaultMsg) defaultMsg.style.display = 'none';
                    sendMessage();
                };
                suggContainer.appendChild(btn);
            });
            suggContainer.classList.remove('hidden');
        }
    } catch(e) {
        console.error("Failed to load suggestions:", e);
    }
});


function addLog(title, content, type) {
    const logDiv = document.createElement('div');
    logDiv.classList.add('log-entry', type);
    
    const h4 = document.createElement('h4');
    h4.textContent = title;
    
    const pre = document.createElement('pre');
    pre.textContent = content;
    
    logDiv.appendChild(h4);
    logDiv.appendChild(pre);
    
    memoryLogs.appendChild(logDiv);
    memoryLogs.scrollTop = memoryLogs.scrollHeight;
}

async function sendMessage() {
    const text = userInput.value.trim();
    if (!text) return;

    // UI Updates
    addMessage(text, 'user');
    playSendSound();
    
    userInput.value = '';
    userInput.disabled = true;
    sendBtn.disabled = true;
    
    typingIndicator.classList.remove('hidden');
    chatBox.scrollTop = chatBox.scrollHeight;

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: text })
        });

        const data = await response.json();
        
        typingIndicator.classList.add('hidden');
        
        if (data.error) {
            addMessage(data.error, 'ai');
        } else {
            addMessage(data.response, 'ai');
            playReceiveSound();
            speakText(data.response);
            
            // Highlight Code blocks
            if (window.hljs) {
                document.querySelectorAll('pre code').forEach((block) => {
                    hljs.highlightElement(block);
                });
            }
            
            // Log Memory Actions
            if (data.relevant_memory) {
                addLog('Memory Retrieved', data.relevant_memory, 'retrieval');
            }
            
            let extractions = [];
            if (data.extracted_facts && data.extracted_facts.length > 0) {
                extractions.push("Facts: " + data.extracted_facts.join(', '));
            }
            if (data.extracted_prefs && data.extracted_prefs.length > 0) {
                extractions.push("Prefs: " + data.extracted_prefs.join(', '));
            }
            
            if (extractions.length > 0) {
                addLog('Memory Extracted & Saved', extractions.join('\n'), 'extraction');
            }

            // Render agent trace in sidebar
            if (data.agent_trace && typeof renderTrace === 'function') {
                renderTrace(data.agent_trace);
            }
        }
    } catch (err) {
        typingIndicator.classList.add('hidden');
        addMessage('Error connecting to the server.', 'ai');
        console.error(err);
    } finally {
        userInput.disabled = false;
        sendBtn.disabled = false;
        userInput.focus();
    }
}

sendBtn.addEventListener('click', sendMessage);
userInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        sendMessage();
    }
});
