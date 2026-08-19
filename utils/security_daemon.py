import os
import sys
import hashlib
import time
import threading
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass


class SecurityDaemon:
    def __init__(self, app=None):
        self.app = app
        self.monitored_files = []
        self.baselines = {}
        self.is_running = False
        self.check_interval = 3600  # Varsayilan: 1 saat (Saniye cinsinden)
        self.admin_email = None
        self.smtp_config = {}
        
        # Proje ana dizinini bul
        self.base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
        
        # Izlenecek kod dosyalarini dinamik olarak bul (.py uzantili dosyalar)
        self.files_to_watch = self._find_all_py_files()
        
        self._load_config()
        self._generate_baselines()

    def _find_all_py_files(self):
        """Proje altindaki tum .py uzantili kod dosyalarini dinamik olarak bulur."""
        py_files = []
        # Taramadan haric tutulacak klasorler
        exclude_dirs = {'.venv', 'venv', 'node_modules', '__pycache__', '.git', 'scratch', 'tests'}
        
        for root, dirs, files in os.walk(self.base_dir):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            for file in files:
                if file.endswith('.py'):
                    py_files.append(os.path.join(root, file))
        return py_files

    def _load_config(self):
        """Cevresel degiskenlerden guvenlik yapilandirmasini yukler."""
        self.check_interval = int(os.getenv('SECURITY_CHECK_INTERVAL', '3600'))
        self.admin_email = os.getenv('ADMIN_EMAIL')
        
        self.smtp_config = {
            'server': os.getenv('SMTP_SERVER'),
            'port': int(os.getenv('SMTP_PORT', '587')),
            'user': os.getenv('SMTP_USER'),
            'pass': os.getenv('SMTP_PASSWORD')
        }

    def _calculate_sha256(self, filepath):
        """Belirtilen dosyanin SHA-256 hash degerini hesaplar."""
        if not os.path.exists(filepath):
            return None
        sha256_hash = hashlib.sha256()
        try:
            with open(filepath, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception as e:
            print(f"[SECURITY DAEMON] Dosya okunurken hata olustu ({os.path.basename(filepath)}): {e}", flush=True)
            return None

    def _generate_baselines(self):
        """Uygulama ilk acildiginda guvenli hash referanslarini (baseline) olusturur."""
        print("\n" + "="*50)
        print("[SECURITY DAEMON] Kod Butunlugu Izleme Sistemi Baslatildi.")
        print("[SECURITY DAEMON] Kritik dosyalar icin guvenli dijital imzalar uretiliyor:")
        
        for filepath in self.files_to_watch:
            filename = os.path.basename(filepath)
            if os.path.exists(filepath):
                file_hash = self._calculate_sha256(filepath)
                self.baselines[filepath] = file_hash
                print(f"  -> {filename}: {file_hash[:16]}...", flush=True)
            else:
                print(f"  [UYARI] Izlenecek dosya bulunamadi: {filename}", flush=True)
        print("="*50 + "\n", flush=True)

    def send_breach_email(self, filename, old_hash, new_hash):
        """Sistem yoneticisine SMTP uzerinden acil durum ihlal maili gonderir."""
        if not self.admin_email or not self.smtp_config['server']:
            print("[SECURITY DAEMON] [BILDIRIM] SMTP yapilandirilmamis, e-posta uyarisi atlandi.", flush=True)
            return False

        try:
            msg = MIMEMultipart()
            msg['From'] = self.smtp_config['user']
            msg['To'] = self.admin_email
            msg['Subject'] = "🔴 ACIL: Siber Guvenlik Ihlali Tespiti - Rent A Car SaaS"

            body = f"""
            <h3>🔴 SIBER GUVENLIK IHLALI TESPIT EDILDI</h3>
            <p>Rent A Car SaaS uygulamasinin yuklu oldugu sunucuda kritik bir kaynak kod dosyasinin izinsiz olarak degistirildigi tespit edilmistir!</p>
            <table border="1" cellpadding="5" style="border-collapse: collapse;">
                <tr style="background-color: #f8d7da; color: #721c24;">
                    <th>Degisen Dosya</th>
                    <td><b>{filename}</b></td>
                </tr>
                <tr>
                    <th>Orijinal Imza (SHA-256)</th>
                    <td><code>{old_hash}</code></td>
                </tr>
                <tr style="color: red;">
                    <th>Yeni/Zararli Imza (SHA-256)</th>
                    <td><code>{new_hash}</code></td>
                </tr>
                <tr>
                    <th>Tespit Tarihi</th>
                    <td>{time.strftime('%Y-%m-%d %H:%M:%S')}</td>
                </tr>
            </table>
            <p><b>Alinan Aksiyon:</b> Sistem, kod enjeksiyonunu ve yetkisiz sizmalari onlemek amaciyla <b>sunucuyu ve uygulamayi otomatik olarak derhal kapatmistir.</b></p>
            <hr>
            <p><i>Bu e-posta Zyronova Rent-A-Car Security Daemon tarafindan otomatik olarak gonderilmistir.</i></p>
            """
            msg.attach(MIMEText(body, 'html', 'utf-8'))

            # SMTP Baglantisi kur
            with smtplib.SMTP(self.smtp_config['server'], self.smtp_config['port'], timeout=10) as server:
                server.starttls()
                server.login(self.smtp_config['user'], self.smtp_config['pass'])
                server.sendmail(self.smtp_config['user'], self.admin_email, msg.as_string())
            
            print(f"[SECURITY DAEMON] Kritik ihlal bildirimi basariyla gonderildi: {self.admin_email}", flush=True)
            return True
        except Exception as err:
            print(f"[SECURITY DAEMON] [HATA] E-posta gonderme basarisiz oldu: {err}", flush=True)
            return False

    def log_breach(self, filepath, old_hash, new_hash):
        """Mudahaleyi guvenlik log dosyasina kalici olarak yazar."""
        log_path = os.path.join(self.base_dir, 'security_breach.log')
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        filename = os.path.basename(filepath)
        
        log_entry = f"[{timestamp}] [!!!] SIBER GUVENLIK IHLALI! Dosya degistirildi: {filename}\n"
        log_entry += f"  Orijinal SHA-256: {old_hash}\n"
        log_entry += f"  Yeni SHA-256:     {new_hash}\n"
        log_entry += f"  AKSIYON: Sistem kapatildi (Self-Termination).\n"
        log_entry += "="*70 + "\n"
        
        try:
            with open(log_path, 'a', encoding='utf-8') as log_file:
                log_file.write(log_entry)
            print(f"[SECURITY DAEMON] Ihlal kayitlari basariyla diske yazildi: security_breach.log", flush=True)
        except Exception as e:
            print(f"[SECURITY DAEMON] Log yazma hatasi: {e}", flush=True)

    def scan_files(self):
        """Tum kritik dosyalari mevcut halleriyle tarar ve imza kontrolu yapar."""
        for filepath in self.files_to_watch:
            filename = os.path.basename(filepath)
            if not os.path.exists(filepath):
                # Eger dosya tamamen silinmisse ihlal kabul et
                self._handle_breach(filepath, self.baselines.get(filepath), "DELETED")
                return False
                
            current_hash = self._calculate_sha256(filepath)
            baseline_hash = self.baselines.get(filepath)
            
            if current_hash != baseline_hash:
                # IMZALAR UYUSMUYOR! MUDAHALE TESPIT EDILDI!
                self._handle_breach(filepath, baseline_hash, current_hash)
                return False
        return True

    def _handle_breach(self, filepath, old_hash, new_hash):
        """Ihlal durumundaki acil durum aksiyonlarini tetikler."""
        filename = os.path.basename(filepath)
        print("\n" + "!"*60)
        print(f"[!!!] SIBER GUVENLIK IHLALI TESPIT EDILDI! Dosya Degistirilmis: {filename}")
        print(f"   Eski Imza: {old_hash}")
        print(f"   Yeni Imza: {new_hash}")
        print("!"*60 + "\n", flush=True)
        
        # 1. Log kaydini olustur
        self.log_breach(filepath, old_hash, new_hash)
        
        # 2. Yoneticiye acil durum uyarisini gonder
        self.send_breach_email(filename, old_hash, new_hash)
        
        # 3. KOD ENJEKSIYONUNUN CALISMASINI ONLEMEK ICIN SISTEMI KAPAT (Self-Termination)
        print("[SECURITY DAEMON] Guvenlik ihlali nedeniyle sistem durduruluyor...", flush=True)
        os._exit(1)

    def monitor_loop(self):
        """Guvenlik taramasini arka planda surekli calistiran dongu."""
        # Ilk kontrolu yapmadan once sunucunun tamamen baslamasi icin 5 saniye bekle
        time.sleep(5)
        
        while self.is_running:
            # Yapilandirmayi her dongude yeniden oku (.env guncellemelerini algilamak icin)
            self._load_config()
            
            # Tarama yap
            self.scan_files()
            
            # Belirlenen sure kadar uyu
            time.sleep(self.check_interval)

    def start(self):
        """Guvenlik thread'ini arka planda baslatir."""
        if not self.is_running:
            self.is_running = True
            self.daemon_thread = threading.Thread(target=self.monitor_loop, daemon=True)
            self.daemon_thread.start()
            print(f"[SECURITY DAEMON] Arka plan tarayicisi {self.check_interval} saniye araliklarla calisacak sekilde baslatildi.", flush=True)

def init_security_daemon(app=None):
    """Flask uygulamasindan guvenlik sistemini tek tikla baslatmak icin yardimci fonksiyon."""
    daemon = SecurityDaemon(app)
    daemon.start()
    return daemon
