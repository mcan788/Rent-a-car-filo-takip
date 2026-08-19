# 💻 ZYRONOVA Rent A Car System: Yerel Kurulum ve Çalıştırma Kılavuzu

Bu kılavuz, Zyronova SaaS Rent a Car uygulamasını kendi Windows bilgisayarınızda (local) sıfır hata ile nasıl çalıştıracağınızı adım adım göstermektedir.

---

## 🛠️ Adım 1: SQL Server Hizmetini Kontrol Edin
Uygulama yerel veritabanı olarak **SQL Server Express** kullanmaktadır. 
1.  Klavyenizden `Windows Tuşu + R` basıp `services.msc` yazın ve Enter'a basın.
2.  Listeden **SQL Server (SQLEXPRESS)** hizmetini bulun.
3.  Eğer durumu "Çalışıyor" değilse, sağ tıklayıp **Başlat** deyin.

> [!NOTE]
> `.env` dosyanızda SQL Server adınız varsayılan olarak **`WIN-HHIJ7MIVESP\SQLEXPRESS`** olarak ayarlanmıştır. Eğer kendi bilgisayarınızdaki SQL Server adı farklıysa (örneğin `localhost` veya `DESKTOP-XXXX\SQLEXPRESS` ise), `.env` dosyasını açıp `DB_SERVER=KENDI_SUNUCU_ADINIZ` şeklinde güncelleyin.

---

## 📦 Adım 2: Sanal Ortamı Aktif Edin ve Kütüphaneleri Yükleyin
Proje dizininde sizin için önceden oluşturulmuş bir sanal Python ortamı (`.venv`) mevcuttur.

1.  **Terminalinizi Açın:** VS Code terminalini veya bilgisayarınızda **PowerShell / CMD** açarak proje klasörüne gidin:
    ```powershell
    cd "C:\Users\MCan\Desktop\Muhammet Can\rent_a_car (1)\rent_a_car"
    ```
2.  **Sanal Ortamı (Virtual Environment) Aktif Edin:**
    *   **PowerShell için:**
        ```powershell
        .\.venv\Scripts\Activate.ps1
        ```
    *   **CMD için:**
        ```cmd
        .\.venv\Scripts\activate.bat
        ```
3.  **Gerekli Kütüphaneleri Yükleyin:**
    ```bash
    pip install -r requirements.txt
    ```

---

## 🗄️ Adım 3: Veritabanını İlklendirin (Sıfırdan Kurulum)
Veritabanı tablolarını, Master şemaları ve ilk örnek şirketleri oluşturmak için ilklendirme scriptini çalıştırın:
```bash
python init_db.py
```
Bu komut sırasıyla:
*   `ZYRONOVA_MASTER` veritabanını oluşturur.
*   Master tabloları (Şirketler ve Kullanıcılar) açar.
*   `www` alt alan adına sahip ilk müşterinizin (tenant) bağımsız veritabanını oluşturur.
*   **Kullanıcı Adı:** `admin` | **Şifre:** `admin123` olan bir master kullanıcı tanımlar.

*(İsteğe bağlı)* Sistemde test verileri (örnek araçlar, aktif kiralamalar, servis kayıtları) görmek isterseniz şu komutla veritabanını doldurabilirsiniz:
```bash
python reseed_data.py
```

---

## 🚀 Adım 4: Uygulamayı Yerelde Başlatın

Uygulamayı geliştirme modunda (sıcak yükleme ve hata ayıklama aktif şekilde) başlatmak için:
```bash
python app.py
```
Sunucu yerel olarak **`5000`** portunda çalışmaya başlayacaktır.

---

## 🌐 Adım 5: Tarayıcıdan Erişim (Çoklu Acenteli Giriş Kuralları)

Sistemimiz **SaaS (Multi-Tenant)** mimarisine sahip olduğu için tarayıcıda girdiğiniz adrese göre farklı paneller açılır:

1.  **👑 Master Yönetim Paneli (SaaS Sahibi - Siz):**
    *   **Adres:** `http://localhost:5000` veya `http://127.0.0.1:5000`
    *   Burada sisteme kayıtlı tüm rent-a-car şirketlerini, lisans sürelerini, ödemelerini görebilir ve yeni acenteler ekleyebilirsiniz.
    *   **Giriş:** `admin` / `admin123`

2.  **🚗 Müşteri / Acente Paneli (Zyronova Merkez Şirketi):**
    *   **Adres:** `http://www.localhost:5000`
    *   Burası ilk rent-a-car müşterinizin araç filosunu, kiralamalarını, kasa durumlarını ve KABİS entegrasyonunu yönettiği paneldir.
    *   **Giriş:** Acente yöneticisi bilgileriyle giriş yapılır.

> [!TIP]
> Modern tarayıcılar (Chrome, Edge, Firefox) `*.localhost` uzantısını otomatik olarak yerel makinenize (`127.0.0.1`) yönlendirir. Bu yüzden `http://www.localhost:5000` adresine yazdığınız an sistem yerel sunucunuza kusursuzca bağlanacaktır!
