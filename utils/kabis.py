import xml.etree.ElementTree as ET
from xml.dom import minidom
import os

class KabisManager:
    """
    EGM KABİS (Kiralık Araç Bildirim Sistemi) Entegrasyon Yöneticisi.
    Bu modül, araç kiralama verilerini EGM standartlarına uygun XML formatına dönüştürür
    ve doğrudan EGM Web Servisi (SOAP WSDL) entegrasyonu için istemci sunar.
    """

    @staticmethod
    def generate_kabis_xml(rental):
        """
        Kiralama kaydını EGM KABİS standartlarında XML dosyasına dönüştürür.
        Bu dosya manuel olarak KABİS web portalına (arackiralama.egm.gov.tr) yüklenebilir.
        """
        root = ET.Element("KabisKiralamaBildirim")
        
        # Şirket / Acente Bilgileri (KABİS Vergi No)
        from flask import g
        company_tax_no = "0000000000"
        if g and hasattr(g, "current_company") and g.current_company:
            company_tax_no = g.current_company.tax_no or "0000000000"
            
        acente = ET.SubElement(root, "AcenteBilgileri")
        ET.SubElement(acente, "VergiNo").text = str(company_tax_no)
        
        # Araç Bilgileri
        arac = ET.SubElement(root, "AracBilgileri")
        ET.SubElement(arac, "Plaka").text = str(rental.plaka).replace(" ", "").upper()
        ET.SubElement(arac, "Marka").text = str(rental.marka or "")
        ET.SubElement(arac, "Model").text = str(rental.model or "")
        ET.SubElement(arac, "VerilisteKm").text = str(rental.verilisteKm or 0)

        # Sürücü (Kiracı) Bilgileri
        surucu = ET.SubElement(root, "SurucuBilgileri")
        ET.SubElement(surucu, "Ad").text = str(rental.isim or "").upper()
        ET.SubElement(surucu, "Soyad").text = str(rental.soyisim or "").upper()
        ET.SubElement(surucu, "KimlikNo").text = str(rental.tcKimlik or "")
        # Normalize nationality to official EGM KABİS standards
        uyruk = str(rental.uyruk or "TC").upper()
        if uyruk in ["TÜRKİYE", "TÜRKIYE", "TURKEY", "TURKISH", "TÜRK", "TURK", "TR"]:
            uyruk = "TC"
            
        ET.SubElement(surucu, "Uyruk").text = uyruk
        ET.SubElement(surucu, "BabaAdi").text = str(getattr(rental, "babaAdi", "")).upper()
        ET.SubElement(surucu, "AnneAdi").text = str(getattr(rental, "anneAdi", "")).upper()
        ET.SubElement(surucu, "DogumTarihi").text = str(getattr(rental, "dogumTarihi", "")) # YYYY-MM-DD
        
        # Ehliyet Bilgileri
        ehliyet = ET.SubElement(surucu, "EhliyetBilgileri")
        ET.SubElement(ehliyet, "BelgeNo").text = str(rental.ehliyetNo or "")
        ET.SubElement(ehliyet, "Sinif").text = str(getattr(rental, "ehliyetSinifi", "B")).upper()
        ET.SubElement(ehliyet, "VerilisTarihi").text = str(rental.ehliyetVerilisTarihi or "")

        # Kiralama Detayları
        kiralama = ET.SubElement(root, "KiralamaDetaylari")
        ET.SubElement(kiralama, "BaslangicTarihi").text = f"{rental.baslangicTarihi} {rental.baslangicSaati or '09:00'}"
        ET.SubElement(kiralama, "BitisTarihi").text = f"{rental.bitisTarihi} {rental.bitisSaati or '09:00'}"
        ET.SubElement(kiralama, "SureGun").text = str(rental.kiralamaSuresi or 1)

        # XML dökümanını güzelleştirerek metne dönüştür
        xml_str = ET.tostring(root, encoding="utf-8")
        parsed = minidom.parseString(xml_str)
        pretty_xml = parsed.toprettyxml(indent="  ")
        
        # EGM KABİS portalı yükleme hatalarını önlemek için XML deklarasyonunu kaldır
        if pretty_xml.startswith("<?xml"):
            lines = pretty_xml.split("\n")
            pretty_xml = "\n".join(lines[1:])
        return pretty_xml.strip()

    @staticmethod
    def send_to_kabis_soap(rental, username, password, company_code, egm_endpoint="https://arackiralama.egm.gov.tr/kabis.asmx?WSDL"):
        """
        EGM SOAP Web Servisini çağırarak kiralamayı doğrudan EGM veritabanına bildirir.
        Gereksinimler:
          - EGM'den alınmış geçerli bir XML Web Servis Yetkisi (Kullanıcı adı, şifre, kod)
          - Sunucunun Sabit IP adresi (EGM güvenlik duvarı IP bazlı beyaz liste kullanır)
          - 'zeep' kütüphanesi (pip install zeep)
        """
        try:
            from zeep import Client
            from zeep.transports import Transport
            import requests

            # TLS sertifikaları ve IP doğrulaması için özel session
            session = requests.Session()
            session.verify = True  # EGM resmi SSL sertifikasını doğrular
            
            # SOAP İstemcisi
            client = Client(egm_endpoint, transport=Transport(session=session))
            
            # SOAP Gönderim Paketi
            kabis_payload = {
                "KullaniciAdi": username,
                "Sifre": password,
                "SirketKodu": company_code,
                "Plaka": str(rental.plaka).replace(" ", "").upper(),
                "TCKimlikNo": rental.tcKimlik,
                "Ad": str(rental.isim).upper(),
                "Soyad": str(rental.soyisim).upper(),
                "EhliyetNo": rental.ehliyetNo,
                "KiralamaBaslangic": f"{rental.baslangicTarihi}T{rental.baslangicSaati or '09:00'}:00",
                "KiralamaBitis": f"{rental.bitisTarihi}T{rental.bitisSaati or '09:00'}:00",
                "Sure": int(rental.kiralamaSuresi or 1),
                "VerilisTarihi": rental.ehliyetVerilisTarihi,
                "Enlem": getattr(rental, "kiralama_lat", 0.0),
                "Boylam": getattr(rental, "kiralama_lng", 0.0)
            }
            
            # EGM Web Servisi Üzerindeki Metodu Çağır (Örn: BildirimKaydet)
            response = client.service.BildirimKaydet(kabis_payload)
            
            # EGM yanıtını kontrol et
            if response and getattr(response, "SonucKodu", 0) == 1:
                return {
                    "success": True,
                    "message": "KABİS Bildirimi Başarıyla Tamamlandı.",
                    "log_id": getattr(response, "KayıtReferansNo", "")
                }
            else:
                return {
                    "success": False,
                    "message": f"KABİS Bildirim Hatası: {getattr(response, 'Aciklama', 'Bilinmeyen Hata')}"
                }
        except ImportError:
            return {
                "success": False,
                "message": "KABİS Web Servis bağlantısı için 'zeep' kütüphanesi kurulu olmalıdır."
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"EGM Web Servisi ile bağlantı kurulamadı: {str(e)}"
            }

    @staticmethod
    def send_return_to_kabis_soap(rental, username, password, company_code, egm_endpoint="https://arackiralama.egm.gov.tr/kabis.asmx?WSDL"):
        """
        Araç teslim alındığında EGM SOAP Web Servisini çağırarak aracı sistemden düşürür.
        """
        try:
            from zeep import Client
            from zeep.transports import Transport
            import requests

            session = requests.Session()
            session.verify = True
            
            client = Client(egm_endpoint, transport=Transport(session=session))
            
            kabis_payload = {
                "KullaniciAdi": username,
                "Sifre": password,
                "SirketKodu": company_code,
                "Plaka": str(rental.plaka).replace(" ", "").upper(),
                "TCKimlikNo": rental.tcKimlik,
                "DonusTarihi": f"{rental.bitisTarihi}T{rental.bitisSaati or '09:00'}:00",
                "DonusKm": rental.alinistaKm,
                "Enlem": getattr(rental, "teslim_lat", 0.0),
                "Boylam": getattr(rental, "teslim_lng", 0.0)
            }
            
            # EGM Web Servisi Arac Teslim Metodu (Örn: AracTeslimBildirim)
            response = client.service.AracTeslimBildirim(kabis_payload)
            
            if response and getattr(response, "SonucKodu", 0) == 1:
                return {
                    "success": True,
                    "message": "KABİS Teslim Bildirimi Başarıyla Tamamlandı."
                }
            else:
                return {
                    "success": False,
                    "message": f"KABİS Teslim Bildirim Hatası: {getattr(response, 'Aciklama', 'Bilinmeyen Hata')}"
                }
        except ImportError:
            return {"success": False, "message": "KABİS Web Servis bağlantısı için 'zeep' kütüphanesi kurulu olmalıdır."}
        except Exception as e:
            return {"success": False, "message": f"EGM Web Servisi ile bağlantı kurulamadı: {str(e)}"}
