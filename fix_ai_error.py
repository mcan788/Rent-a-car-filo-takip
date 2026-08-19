import re

html_path = r'C:\SUNUCU_PAKETI\RentACar_Sistem\blueprints\ai.py'

with open(html_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace exception handler
new_handler = """
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        with open('C:\\\\SUNUCU_PAKETI\\\\ai_error.log', 'w', encoding='utf-8') as f:
            f.write(tb)
        print(f"AI Chat Error: {e}")
        return jsonify({'success': False, 'error': f'AI Error: {str(e)}'}), 500
"""

# Find except block
import re
content = re.sub(r'    except Exception as e:.*', new_handler.strip(), content, flags=re.DOTALL)

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(content)
print('Updated ai.py to return error')
