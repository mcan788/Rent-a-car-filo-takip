import re

html_path = r'C:\SUNUCU_PAKETI\TurTakip_Arayuz\client\public\zyronova_premium.html'

with open(html_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace input HTML with inline styles
new_html = '''
        <div class="chat-input-container" style="display: flex !important; align-items: center !important; background: rgba(255, 255, 255, 0.05) !important; border-top: 1px solid rgba(255, 255, 255, 0.1) !important; padding: 10px 15px !important; gap: 12px !important; margin-top: auto;">
            <input type="text" id="chatInput" placeholder="Bir mesaj yazın..." onkeypress="handleChatKeyPress(event)" style="flex: 1 !important; background: transparent !important; border: none !important; color: #ffffff !important; font-size: 0.95rem !important; outline: none !important; padding: 5px !important; box-shadow: none !important;">
            <button id="sendAiBtn" onclick="sendAiMessage()" style="background: #4d79ff !important; color: #ffffff !important; border: none !important; border-radius: 50% !important; width: 36px !important; height: 36px !important; min-width: 36px !important; cursor: pointer !important; display: flex !important; align-items: center !important; justify-content: center !important; transition: all 0.3s ease !important; padding: 0 !important; margin: 0 !important; box-shadow: 0 4px 15px rgba(77, 121, 255, 0.4) !important;" onmouseover="this.style.transform='scale(1.1)'; this.style.background='#6b8eff'" onmouseout="this.style.transform='scale(1)'; this.style.background='#4d79ff'">
                <i class="fas fa-paper-plane" style="color: #ffffff !important; font-size: 0.9rem !important; margin-left: -2px !important;"></i>
            </button>
        </div>
'''

content = re.sub(r'<div class="chat-input-container">.*?</div>', new_html.strip(), content, flags=re.DOTALL)

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(content)
print('Fixed inline styles successfully')
