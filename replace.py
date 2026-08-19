import codecs
path = r'c:\Users\MCAN\Desktop\Masa Üstü Ana Klasör\Proje Dosyaları\Proje kod dosyaları\Rent A Car - Tur Takip\rent_a_car\templates\profil.html'
with codecs.open(path, 'r', 'utf-8') as f:
    content = f.read()

import re
start_idx = content.find('<div class="form-group">', content.find('name="password"') - 100)
end_idx = content.find('<div style="display: flex; gap: 1rem;">', start_idx)

if start_idx != -1 and end_idx != -1:
    new_html = '''<div class="form-group">
                  <label style="font-weight: 700; margin-bottom: 0.5rem; display: block; font-size: 0.85rem;">Şifre</label>
                  <input type="password" name="password" class="form-control" placeholder="********" required style="width: 100%; padding: 0.85rem; border-radius: 12px; border: 1px solid #e2e8f0;">
                </div>
                
                {% if current_user.company_id == 1 %}
                <div class="form-group">
                  <label style="font-weight: 700; margin-bottom: 0.5rem; display: block; font-size: 0.85rem;">Departman / Modül</label>
                  <select name="company_id" id="departmentSelect" class="form-control" style="width: 100%; padding: 0.85rem; border-radius: 12px; border: 1px solid #e2e8f0;" onchange="updateRoles()">
                    <option value="1">Yönetim / Merkez (Master)</option>
                    <option value="2">Rent A Car Departmanı</option>
                    <option value="3">Tur Takip Departmanı</option>
                  </select>
                </div>
                {% endif %}

                <div class="form-group">
                  <label style="font-weight: 700; margin-bottom: 0.5rem; display: block; font-size: 0.85rem;">Rol</label>
                  <select name="role_id" id="roleSelect" class="form-control" style="width: 100%; padding: 0.85rem; border-radius: 12px; border: 1px solid #e2e8f0;">
                    {% if current_user.company_id == 1 %}
                      <option value="13" data-dept="1">Personel (Merkez)</option>
                      <option value="12" data-dept="1">Admin (Merkez)</option>
                      {% if current_user.is_super_admin %}
                      <option value="11" data-dept="1">Süper Admin</option>
                      {% endif %}
                      
                      <option value="22" data-dept="2" style="display:none;">Rent A Car Personel</option>
                      <option value="21" data-dept="2" style="display:none;">Rent A Car Yönetici</option>
                      
                      <option value="32" data-dept="3" style="display:none;">Tur Takip Personel</option>
                      <option value="31" data-dept="3" style="display:none;">Tur Takip Yönetici</option>
                    {% else %}
                      <option value="22">Rent A Car Personel</option>
                      <option value="21">Rent A Car Yönetici</option>
                      <option value="32">Tur Takip Personel</option>
                      <option value="31">Tur Takip Yönetici</option>
                    {% endif %}
                  </select>
                </div>
              </div>

              <script>
                function updateRoles() {
                  const dept = document.getElementById('departmentSelect');
                  if (!dept) return;
                  const roleSelect = document.getElementById('roleSelect');
                  const deptId = dept.value;
                  
                  let firstVisible = null;
                  for (let i = 0; i < roleSelect.options.length; i++) {
                    const opt = roleSelect.options[i];
                    if (opt.getAttribute('data-dept') === deptId) {
                      opt.style.display = '';
                      if (!firstVisible) firstVisible = opt;
                    } else {
                      opt.style.display = 'none';
                    }
                  }
                  if (firstVisible) {
                    roleSelect.value = firstVisible.value;
                  }
                }
                
                document.addEventListener('DOMContentLoaded', updateRoles);
              </script>
              '''
    
    new_content = content[:start_idx] + new_html + content[end_idx:]
    with codecs.open(path, 'w', 'utf-8') as f:
        f.write(new_content)
    print('SUCCESS')
else:
    print('FAILED TO FIND INDICES', start_idx, end_idx)
