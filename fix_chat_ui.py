import re

html_path = r'C:\SUNUCU_PAKETI\TurTakip_Arayuz\client\public\zyronova_premium.html'

with open(html_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Improved CSS with higher specificity
improved_css = '''
        /* AI Chatbot Custom Input */
        .chat-input-container {
            display: flex !important;
            align-items: center !important;
            background: rgba(255, 255, 255, 0.05) !important;
            border-top: 1px solid rgba(255, 255, 255, 0.1) !important;
            padding: 10px 15px !important;
            gap: 12px !important;
            margin-top: auto; /* Push to bottom */
        }
        #chatInput {
            flex: 1 !important;
            background: transparent !important;
            border: none !important;
            color: #ffffff !important;
            font-size: 0.95rem !important;
            outline: none !important;
            padding: 5px !important;
        }
        #chatInput::placeholder {
            color: rgba(255, 255, 255, 0.5) !important;
        }
        #sendAiBtn {
            background: var(--blue) !important;
            color: #ffffff !important;
            border: none !important;
            border-radius: 50% !important;
            width: 36px !important;
            height: 36px !important;
            min-width: 36px !important;
            cursor: pointer !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            transition: all 0.3s ease !important;
            padding: 0 !important;
            margin: 0 !important;
            box-shadow: 0 4px 15px rgba(77, 121, 255, 0.4) !important;
        }
        #sendAiBtn i {
            color: #ffffff !important;
            font-size: 0.9rem !important;
            margin-left: -2px !important;
        }
        #sendAiBtn:hover {
            transform: scale(1.1) !important;
            background: #6b8eff !important;
        }
'''

# Check if improved css is already there, if not append it
if '/* AI Chatbot Custom Input */' not in content:
    content = content.replace('</style>', improved_css + '\n    </style>')

# Replace input HTML to add the id to the button
new_html = '''
          <div class="chat-input-container">
              <input type="text" id="chatInput" placeholder="Bir mesaj yazın..." onkeypress="handleChatKeyPress(event)">
              <button id="sendAiBtn" onclick="sendAiMessage()"><i class="fas fa-paper-plane"></i></button>
          </div>
'''
content = re.sub(r'<div class="chat-input-container">.*?</div>', new_html.strip(), content, flags=re.DOTALL)


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
                const response = await fetch('/py-api/chat', {
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

if 'async function sendAiMessage' not in content:
    content = content.replace('function askBot', ai_js + '\n        function askBot')

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(content)
print('Fixed JS and CSS successfully')
