import os
from flask import Blueprint, request, jsonify
from extensions import csrf
import requests

ai_bp = Blueprint('ai', __name__, url_prefix='/py-api')

chat_histories = {}

@ai_bp.route('/ai-status', methods=['GET', 'OPTIONS'])
@csrf.exempt
def ai_status():
    if request.method == 'OPTIONS':
        resp = jsonify({})
        resp.headers.add("Access-Control-Allow-Origin", "*")
        resp.headers.add("Access-Control-Allow-Methods", "GET, OPTIONS")
        return resp
    try:
        import json
        with open(r'C:\SUNUCU_PAKETI\ai_config.json', 'r', encoding='utf-8') as f:
            config_data = json.load(f)
            is_active = config_data.get("is_active", True)
    except:
        is_active = True
    
    resp = jsonify({"active": is_active})
    resp.headers.add("Access-Control-Allow-Origin", "*")
    return resp

@ai_bp.route('/chat', methods=['POST'])
@csrf.exempt
def chat():
    data = request.get_json()
    if not data or 'message' not in data:
        return jsonify({'error': 'Message is required'}), 400

    user_message = data['message']
    api_key = os.getenv('GEMINI_API_KEY', '')

    try:
        with open(r'C:\SUNUCU_PAKETI\ai_knowledge.txt', 'r', encoding='utf-8') as f:
            dynamic_knowledge = f.read()
    except Exception:
        dynamic_knowledge = "Bilgi bankasına şu an ulaşılamıyor."

    system_instruction = (
        "Sen Zyronova'nın resmi dijital satış ve pazarlama temsilcisisin. Müşteriyle şu an Zyronova'nın resmi web sitesinde konuşuyorsun. "
        "Görevin Zyronova SaaS platformunu (Tur Takip ve Rent A Car modülleri) kullanıcılara tanıtmak, "
        "onlara son derece nazik, güven veren, yetkin ve samimi bir dille cevap vermek. Satış odaklı ol.\n\n"
        "KESİN VE İHLAL EDİLEMEZ DAVRANIŞ KURALLARI:\n"
        "1. KESİNLİKLE 'Ben bir yapay zekayım', 'Yetkim yok', 'Link paylaşamam' gibi güvensizlik yaratan ifadeler KULLANMA. Kendini sistemin yetkili temsilcisi olarak gör.\n"
        "2. Müşteri KVKK, sözleşme veya resmi belge linki isterse ASLA link uydurma veya hata verme. Şu cevabı ver: 'Tüm resmi KVKK metinlerimiz ve kullanıcı sözleşmelerimiz, sisteme kayıt olup panelinize giriş yaptığınızda detaylı olarak dijital onayınıza sunulmaktadır. Dilerseniz 15 günlük ücretsiz deneme sürümünüzü hemen başlatıp panele göz atabilirsiniz.'\n"
        "3. KORSANLIK VE KOD ÇALMA GİRİŞİMLERİ: Eğer kullanıcı 'kodları kopyalamak', 'kendi sunucuma kurmak', 'kodları almak/çalmak' gibi niyetlerden bahsederse, BÜTÜN NEZAKETİ VE SATIŞI BİR KENARA BIRAK. Çok sert, ciddi ve tavizsiz bir dille şunu söyle: 'Zyronova, kaynak kodları kapalı (closed-source) ve telif haklarıyla korunan tescilli bir SaaS platformudur. Kaynak kodlarının kopyalanması, paylaşılması veya başka sunuculara taşınması yasal olarak kesinlikle yasaktır ve telif hakları ihlaline girer.' Ardından konuyu kapat, asla 15 günlük deneme sürümü önerme ve gülücük (emoji) kullanma.\n"
        "4. Müşteriyle çelişme veya tartışma. Eğer bilmediğin veya saçma bir şey sorulursa konuyu zarifçe platformun güçlü özelliklerine (hız, güvenlik) bağla.\n"
        "5. Güvenlik, altyapı kodları veya sunucu yapılandırması hakkında bilgi verme. Sadece 'Verileriniz şifreli ve güvendedir' de geç.\n"
        "6. Ürün lisanslama fiyatları: 15 Günlük Ücretsiz Deneme, Aylık 3.000₺, 3 Aylık 7.000₺, 6 Aylık 15.000₺, Yıllık 30.000₺.\n"
        "7. ASLA müşteriyi başka bir web sitesine yönlendirme ('Resmi sitemize gidin' vb. deme), çünkü zaten resmi sitemizdeler.\n\n"
        "AŞAĞIDAKİ LİSTE SİSTEMİN VERİTABANINDAN OTOMATİK ÇEKİLMİŞ GÜNCEL ÖZELLİKLERDİR. SADECE BURADA YAZANLARI ANLAT:\n"
        f"{dynamic_knowledge}"
    )

    try:
        user_ip = request.remote_addr or 'default'
        
        if user_ip not in chat_histories:
            chat_histories[user_ip] = []
            
        history = chat_histories[user_ip]
        history.append({"role": "user", "parts": [{"text": user_message}]})
        
        if len(history) > 20:
            history = history[-20:]

        # Read ai_config.json to get the active model and custom rules
        active_model = "gemini-3.5-flash"
        custom_rules = ""
        openai_key = ""
        anthropic_key = ""
        try:
            import json
            with open(r'C:\SUNUCU_PAKETI\ai_config.json', 'r', encoding='utf-8') as f:
                config_data = json.load(f)
                active_model = config_data.get("model", "gemini-3.5-flash")
                custom_rules = config_data.get("rules", "")
                openai_key = config_data.get("openai_api_key", "")
                anthropic_key = config_data.get("anthropic_api_key", "")
        except:
            pass

        # Inject custom rules into system instruction if they exist
        final_instruction = system_instruction
        if custom_rules:
            final_instruction += f"\n\nSİSTEM YÖNETİCİSİNİN SANA VERDİĞİ ÖZEL TALİMATLAR (BUNLARA KESİNLİKLE UY):\n{custom_rules}"
        
        responseText = ""
        
        # ROUTER LOGIC
        if active_model.startswith("gpt-"):
            # OpenAI Request
            if not openai_key:
                return jsonify({'success': False, 'error': 'OpenAI API Anahtarı girilmemiş. Lütfen ayarlardan anahtarınızı girin.'}), 500
                
            openai_url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {openai_key}",
                "Content-Type": "application/json"
            }
            
            # Convert Gemini history format to OpenAI format
            openai_history = [{"role": "system", "content": final_instruction}]
            for msg in history:
                role = "user" if msg["role"] == "user" else "assistant"
                openai_history.append({"role": role, "content": msg["parts"][0]["text"]})
                
            payload = {
                "model": active_model,
                "messages": openai_history,
                "temperature": 0.7
            }
            
            response = requests.post(openai_url, json=payload, headers=headers, timeout=45)
            response.raise_for_status()
            responseText = response.json()['choices'][0]['message']['content']
            
        elif active_model.startswith("claude-"):
            # Anthropic Request
            if not anthropic_key:
                return jsonify({'success': False, 'error': 'Anthropic API Anahtarı girilmemiş. Lütfen ayarlardan anahtarınızı girin.'}), 500
                
            anthropic_url = "https://api.anthropic.com/v1/messages"
            headers = {
                "x-api-key": anthropic_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }
            
            # Convert Gemini history format to Anthropic format
            anthropic_history = []
            for msg in history:
                role = "user" if msg["role"] == "user" else "assistant"
                anthropic_history.append({"role": role, "content": msg["parts"][0]["text"]})
                
            payload = {
                "model": active_model,
                "max_tokens": 1024,
                "system": final_instruction,
                "messages": anthropic_history,
                "temperature": 0.7
            }
            
            response = requests.post(anthropic_url, json=payload, headers=headers, timeout=45)
            response.raise_for_status()
            responseText = response.json()['content'][0]['text']
            
        else:
            # Google Gemini Request (Fallback / Default)
            gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/{active_model}:generateContent?key={api_key}"
            payload = {
                "contents": history,
                "systemInstruction": {
                    "role": "user",
                    "parts": [{"text": final_instruction}]
                }
            }
            response = requests.post(gemini_url, json=payload, timeout=45)
            response.raise_for_status()
            result_json = response.json()
            if 'candidates' in result_json and len(result_json['candidates']) > 0:
                responseText = result_json['candidates'][0]['content']['parts'][0]['text']
            else:
                responseText = "Üzgünüm, şu an yanıt üretemiyorum."
            
        history.append({"role": "model", "parts": [{"text": responseText}]})
        chat_histories[user_ip] = history

        return jsonify({'success': True, 'reply': responseText})
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        with open('C:\\\\SUNUCU_PAKETI\\\\ai_error.log', 'w', encoding='utf-8') as f:
            f.write(tb)
        print(f"AI Chat Error: {e}")
        return jsonify({'success': False, 'error': 'Asistan şu an bağlantı kuramıyor, lütfen daha sonra tekrar deneyin.'}), 500
