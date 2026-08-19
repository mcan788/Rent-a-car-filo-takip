import re

html_path = r'C:\SUNUCU_PAKETI\TurTakip_Arayuz\client\public\zyronova_premium.html'

with open(html_path, 'r', encoding='utf-8') as f:
    content = f.read()

# CSS Injection for the chat input
css_injection = '''
        .chat-input-container {
            display: flex;
            align-items: center;
            background: rgba(255, 255, 255, 0.05);
            border-top: 1px solid rgba(255, 255, 255, 0.1);
            padding: 10px;
            gap: 10px;
        }
        .chat-input-container input {
            flex: 1;
            background: transparent;
            border: none;
            color: white;
            font-size: 0.9rem;
            outline: none;
        }
        .chat-input-container button {
            background: var(--blue);
            color: white;
            border: none;
            border-radius: 50%;
            width: 35px;
            height: 35px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: 0.3s;
        }
        .chat-input-container button:hover {
            transform: scale(1.1);
        }
'''
if '.chat-input-container' not in content:
    content = content.replace('</style>', css_injection + '\n    </style>')

# Replace tags container with input form
new_input_html = '''
        <div class="chat-input-container">
            <input type="text" id="chatInput" placeholder="Bir mesaj yazın..." onkeypress="handleChatKeyPress(event)">
            <button onclick="sendAiMessage()"><i class="fas fa-paper-plane"></i></button>
        </div>
'''
content = re.sub(r'<div class="chat-tags-container">.*?</div>', new_input_html, content, flags=re.DOTALL)

# Add AI javascript function
ai_js = '''
        async function sendAiMessage() {
            const inputField = document.getElementById('chatInput');
            const question = inputField.value.trim();
            if(!question) return;
            
            inputField.value = '';
            
            const messages = document.getElementById('chatMessages');
            
            const userMsg = document.createElement('div');
            userMsg.className = 'chat-msg user';
            userMsg.innerText = question;
            messages.appendChild(userMsg);
            
            const typing = document.createElement('div');
            typing.className = 'typing-indicator';
            typing.id = 'botTyping';
            typing.innerHTML = '<span></span><span></span><span></span>';
            messages.appendChild(typing);
            messages.scrollTop = messages.scrollHeight;
            
            try {
                const response = await fetch('/api/ai/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: question })
                });
                
                const data = await response.json();
                
                const typingIndicator = document.getElementById('botTyping');
                if(typingIndicator) typingIndicator.remove();
                
                const botMsg = document.createElement('div');
                botMsg.className = 'chat-msg bot';
                botMsg.innerText = data.reply || 'Asistan geçici olarak hizmet dışıdır.';
                messages.appendChild(botMsg);
                messages.scrollTop = messages.scrollHeight;
            } catch(e) {
                const typingIndicator = document.getElementById('botTyping');
                if(typingIndicator) typingIndicator.remove();
                
                const botMsg = document.createElement('div');
                botMsg.className = 'chat-msg bot';
                botMsg.innerText = 'Bağlantı hatası oluştu. Lütfen tekrar deneyin.';
                messages.appendChild(botMsg);
                messages.scrollTop = messages.scrollHeight;
            }
        }
        
        function handleChatKeyPress(e) {
            if (e.key === 'Enter') {
                sendAiMessage();
            }
        }
'''

if 'sendAiMessage()' not in content:
    content = content.replace('function askBot', ai_js + '\n        function askBot')

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(content)
print('Updated html successfully')
