import re

html_path = r'C:\SUNUCU_PAKETI\TurTakip_Arayuz\client\public\zyronova_premium.html'

with open(html_path, 'r', encoding='utf-8') as f:
    content = f.read()

# The previous regex `re.sub(r'<div class=\"chat-tags-container\">.*?</div>', ...)` replaced until the FIRST </div>
# Which means it kept all the other chat tags inside the container.
# We need to find the chat tags and remove them.

# Remove all chat-tag divs
while '<div class="chat-tag"' in content:
    s_idx = content.find('<div class="chat-tag"')
    e_idx = content.find('</div>', s_idx) + 6
    if s_idx != -1 and e_idx != -1:
        content = content[:s_idx] + content[e_idx:]
    else:
        break

# Remove any empty chat-tags-container that might be left
content = re.sub(r'<div class="chat-tags-container">\s*</div>', '', content)

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(content)
print('Fixed HTML tags successfully')
