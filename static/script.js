const chatBox = document.getElementById('chat-box');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');
const memoryLogs = document.getElementById('memory-logs');

function addMessage(text, sender) {
    const msgDiv = document.createElement('div');
    msgDiv.classList.add('message', sender);
    msgDiv.textContent = text;
    chatBox.appendChild(msgDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
}

function addLog(title, content, type) {
    const logDiv = document.createElement('div');
    logDiv.classList.add('log-entry', type);
    
    const h4 = document.createElement('h4');
    h4.style.marginBottom = '5px';
    h4.style.color = '#c9d1d9';
    h4.textContent = title;
    
    const pre = document.createElement('pre');
    pre.style.whiteSpace = 'pre-wrap';
    pre.style.fontFamily = 'inherit';
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
    userInput.value = '';
    userInput.disabled = true;
    sendBtn.disabled = true;

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: text })
        });

        const data = await response.json();
        
        if (data.error) {
            addMessage(data.error, 'ai');
        } else {
            addMessage(data.response, 'ai');
            
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
        }
    } catch (err) {
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
