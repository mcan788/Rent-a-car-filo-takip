(function() {
    // Cerez onayi var mi kontrol et
    if (localStorage.getItem('zyronova_kvkk_accepted') === 'true') {
        return;
    }

    // Stil tanimlamasi
    const style = document.createElement('style');
    style.innerHTML = `
        .kvkk-banner-container {
            position: fixed;
            bottom: 24px;
            left: 24px;
            right: 24px;
            background: rgba(15, 23, 42, 0.95);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            color: #f8fafc;
            padding: 20px 28px;
            border-radius: 16px;
            box-shadow: 0 20px 40px -10px rgba(0,0,0,0.3);
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 24px;
            z-index: 9999999;
            font-family: 'Inter', 'Outfit', sans-serif;
            border: 1px solid rgba(255,255,255,0.1);
            transform: translateY(150%);
            transition: transform 0.6s cubic-bezier(0.4, 0, 0.2, 1);
        }
        .kvkk-banner-container.show {
            transform: translateY(0);
        }
        .kvkk-icon {
            font-size: 24px;
            margin-right: 12px;
            flex-shrink: 0;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .kvkk-text-content {
            display: flex;
            align-items: center;
            flex: 1;
        }
        .kvkk-text {
            font-size: 0.9rem;
            line-height: 1.5;
            margin: 0;
            color: #cbd5e1;
        }
        .kvkk-text strong {
            color: #ffffff;
            font-weight: 700;
        }
        .kvkk-text a {
            color: #60a5fa;
            text-decoration: none;
            font-weight: 600;
            transition: color 0.2s;
        }
        .kvkk-text a:hover {
            color: #93c5fd;
            text-decoration: underline;
        }
        .kvkk-buttons {
            display: flex;
            gap: 12px;
            flex-shrink: 0;
        }
        .kvkk-btn {
            padding: 12px 24px;
            border-radius: 12px;
            font-size: 0.9rem;
            font-weight: 600;
            cursor: pointer;
            border: none;
            transition: all 0.2s ease;
            white-space: nowrap;
        }
        .kvkk-btn-accept {
            background: #3b82f6;
            color: white;
            box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
        }
        .kvkk-btn-accept:hover {
            background: #2563eb;
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(59, 130, 246, 0.4);
        }
        @media (max-width: 768px) {
            .kvkk-banner-container {
                flex-direction: column;
                align-items: stretch;
                text-align: left;
                bottom: 0;
                left: 0;
                right: 0;
                border-radius: 20px 20px 0 0;
                padding: 24px 20px;
                gap: 16px;
                border-bottom: none;
                border-left: none;
                border-right: none;
            }
            .kvkk-text-content {
                align-items: flex-start;
            }
            .kvkk-icon {
                margin-top: 2px;
            }
            .kvkk-buttons {
                flex-direction: column;
                width: 100%;
            }
            .kvkk-btn {
                width: 100%;
                text-align: center;
                padding: 14px;
            }
        }
    `;
    document.head.appendChild(style);

    // Banner HTML Elementi
    const banner = document.createElement('div');
    banner.className = 'kvkk-banner-container';
    banner.innerHTML = `
        <div class="kvkk-text-content">
            <div class="kvkk-icon">🍪</div>
            <div class="kvkk-text">
                <strong>Çerez (Cookie) Kullanımı</strong><br>
                Size daha iyi hizmet sunabilmek, site kullanımınızı analiz etmek ve güvenliğinizi sağlamak amacıyla çerezler kullanıyoruz. 
                Detaylı bilgi için <a href="/kvkk-aydinlatma-metni" target="_blank">KVKK Aydınlatma Metni</a>'ni inceleyebilirsiniz. Sitemizi kullanmaya devam ederek çerez kullanımını kabul etmiş olursunuz.
            </div>
        </div>
        <div class="kvkk-buttons">
            <button class="kvkk-btn kvkk-btn-accept" id="kvkk-accept-btn">Anladım, Kabul Ediyorum</button>
        </div>
    `;
    document.body.appendChild(banner);

    // SPA uyumlu KVKK Banner Gösterim Mantığı
    const checkAndShowBanner = () => {
        // Çerez kabul edildiyse bir daha gösterme
        if (localStorage.getItem('zyronova_kvkk_accepted') === 'true') return;
        
        const hiddenPaths = ['/module-selector', '/', '/sso-login'];
        if (hiddenPaths.includes(window.location.pathname)) {
            // Seçim ekranındayız, afişi gizle
            banner.classList.remove('show');
        } else {
            // İlgili modülün içindeyiz, afişi göster
            if (!banner.classList.contains('show')) {
                banner.classList.add('show');
            }
        }
    };

    // Sayfa yüklendikten 1 saniye sonra ilk kontrolü yap
    setTimeout(checkAndShowBanner, 1000);

    // React Router (SPA) sayfa geçişlerini dinlemek için pushState'i kancala (hook)
    const originalPushState = history.pushState;
    history.pushState = function() {
        originalPushState.apply(this, arguments);
        setTimeout(checkAndShowBanner, 100);
    };
    
    // Tarayıcı geri/ileri butonları için popstate dinleyicisi
    window.addEventListener('popstate', () => {
        setTimeout(checkAndShowBanner, 100);
    });

    // Kabul Et butonuna tiklandiginda
    document.getElementById('kvkk-accept-btn').addEventListener('click', () => {
        // Tarayiciya onayi kaydet
        localStorage.setItem('zyronova_kvkk_accepted', 'true');
        
        // Cikis animasyonu
        banner.classList.remove('show');
        
        // Animasyon bitiminde DOM'dan kaldir
        setTimeout(() => {
            banner.remove();
        }, 600);
    });
})();
