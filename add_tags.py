import re

html_path = r'C:\SUNUCU_PAKETI\TurTakip_Arayuz\client\public\zyronova_premium.html'

with open(html_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Insert the tags right after the welcome message in the chatbot
tags_html = """
            <div class="chat-tags-container" id="quickTagsContainer" style="display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; margin-bottom: 10px; padding: 0 15px;">
                <div class="chat-tag" onclick="quickAsk('Tur Takip özellikleri neler?')" style="background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.1); color: #b6c1ea; padding: 6px 12px; border-radius: 100px; font-size: 0.75rem; cursor: pointer; transition: all 0.3s;">Tur Takip özellikleri neler?</div>
                <div class="chat-tag" onclick="quickAsk('Rent A Car sistemi neleri kapsıyor?')" style="background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.1); color: #b6c1ea; padding: 6px 12px; border-radius: 100px; font-size: 0.75rem; cursor: pointer; transition: all 0.3s;">Rent A Car neleri kapsıyor?</div>
                <div class="chat-tag" onclick="quickAsk('Fiyatlandırma nasıl?')" style="background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.1); color: #b6c1ea; padding: 6px 12px; border-radius: 100px; font-size: 0.75rem; cursor: pointer; transition: all 0.3s;">Fiyatlandırma nasıl?</div>
                <div class="chat-tag" onclick="quickAsk('Canlı demo görebilir miyim?')" style="background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.1); color: #b6c1ea; padding: 6px 12px; border-radius: 100px; font-size: 0.75rem; cursor: pointer; transition: all 0.3s;">Canlı demo görebilir miyim?</div>
            </div>
"""

welcome_msg_regex = r'(<div class="chat-msg bot">\s*Merhaba! Ben Zyronova Yapay Zeka Asistanı.*?Aşağıdaki sorulardan birine tıklayabilirsiniz\.\s*</div>)'

# Add hover effect via a small style block inside the container just for these inline tags
tags_html = tags_html + """
            <style>
                .chat-tag:hover {
                    color: white !important;
                    background: rgba(255, 255, 255, 0.15) !important;
                    border-color: rgba(255, 255, 255, 0.3) !important;
                    transform: translateY(-2px);
                }
            </style>
"""

content = re.sub(welcome_msg_regex, r'\1' + '\n' + tags_html, content, count=1)

# 2. Insert quickAsk function right before sendAiMessage
quick_ask_js = """
        function quickAsk(question) {
            const inputField = document.getElementById('chatInput');
            inputField.value = question;
            sendAiMessage();
            
            const tagsContainer = document.getElementById('quickTagsContainer');
            if(tagsContainer) {
                tagsContainer.style.display = 'none';
            }
        }
"""
if "function quickAsk" not in content:
    content = content.replace('async function sendAiMessage() {', quick_ask_js + '\n        async function sendAiMessage() {')

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Tags inserted successfully.")
