import os
import requests
import json

def build_knowledge():
    with open(r'C:\SUNUCU_PAKETI\RentACar_Sistem\models.py', 'r', encoding='utf-8') as f:
        models_content = f.read()

    # Read custom rules and model from config
    custom_rules = ""
    active_model = "gemini-3.5-flash"
    openai_key = ""
    anthropic_key = ""
    
    config_path = r'C:\SUNUCU_PAKETI\ai_config.json'
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
                custom_rules = config_data.get("rules", "").strip()
                active_model = config_data.get("model", "gemini-3.5-flash")
                openai_key = config_data.get("openai_api_key", "")
                anthropic_key = config_data.get("anthropic_api_key", "")
        except:
            pass
    else:
        # Fallback to old txt
        rules_path = r'C:\SUNUCU_PAKETI\ai_custom_rules.txt'
        if os.path.exists(rules_path):
            with open(rules_path, 'r', encoding='utf-8') as f:
                custom_rules = f.read().strip()

    prompt = f'''
Burada bir SaaS uygulamasının veritabanı modelleri bulunuyor. Sadece bu modellere bakarak sistemin hangi özellikleri desteklediğini (örneğin: araç kiralama, bakım takibi, finansal kayıtlar vb.) kısa ve net bir liste halinde çıkar. 
Asla bu kodlarda olmayan bir özelliği uydurma. Sadece olanları listele. 

ÇOK ÖNEMLİ KURALLAR (Aşağıdaki kurallara KESİNLİKLE uymalısın):
{custom_rules}

Modeller:
{models_content}
'''

    api_key = os.getenv('GEMINI_API_KEY', '')
    
    try:
        text = ""
        if active_model.startswith("gpt-"):
            if not openai_key:
                raise Exception("OpenAI API Key is missing")
            openai_url = "https://api.openai.com/v1/chat/completions"
            headers = {"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"}
            payload = {
                "model": active_model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.5
            }
            resp = requests.post(openai_url, json=payload, headers=headers, timeout=30)
            resp.raise_for_status()
            text = resp.json()['choices'][0]['message']['content']
            
        elif active_model.startswith("claude-"):
            if not anthropic_key:
                raise Exception("Anthropic API Key is missing")
            anthropic_url = "https://api.anthropic.com/v1/messages"
            headers = {"x-api-key": anthropic_key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
            payload = {
                "model": active_model,
                "max_tokens": 1024,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.5
            }
            resp = requests.post(anthropic_url, json=payload, headers=headers, timeout=30)
            resp.raise_for_status()
            text = resp.json()['content'][0]['text']
            
        else:
            url = f'https://generativelanguage.googleapis.com/v1beta/models/{active_model}:generateContent?key={api_key}'
            payload = {
                'contents': [{'role': 'user', 'parts': [{'text': prompt}]}]
            }
            resp = requests.post(url, json=payload, timeout=30)
            resp.raise_for_status()
            text = resp.json()['candidates'][0]['content']['parts'][0]['text']
        
        with open(r'C:\SUNUCU_PAKETI\ai_knowledge.txt', 'w', encoding='utf-8') as f:
            f.write(text)
        print("Bilgi bankası güncellendi!")
    except Exception as e:
        print('Hata:', e)

if __name__ == '__main__':
    build_knowledge()

