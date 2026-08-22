/** 하이브리드 광고: 상단·사이드 네트워크, 카드는 PRO 하우스. 성인 광고 배제. */

const ADULT_MARKS = ['adult', 'sexual', 'dating', 'pornography'];
const CONSENT_KEY_FALLBACK = 'cityflow_ad_consent';

const loadScriptOnce = (src, id, attrs = {}) => new Promise((resolve, reject) => {
    if (id && document.getElementById(id)) {
        resolve();
        return;
    }
    const el = document.createElement('script');
    if (id) el.id = id;
    el.async = true;
    el.src = src;
    if (attrs.crossOrigin) el.crossOrigin = attrs.crossOrigin;
    el.onload = () => resolve();
    el.onerror = () => reject(new Error('ad script failed'));
    document.head.appendChild(el);
});

const loadAdsenseScript = (client) => {
    const src = `https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=${encodeURIComponent(client)}`;
    return loadScriptOnce(src, 'adsense-loader', { crossOrigin: 'anonymous' });
};

const displayAdIns = (client, slot, extraClass = '') => {
    const cls = extraClass ? `adsbygoogle ${extraClass}` : 'adsbygoogle';
    return `
    <!-- Display Ads -->
    <ins class="${cls}"
         style="display:block"
         data-ad-client="${client}"
         data-ad-slot="${slot}"
         data-ad-format="auto"
         data-full-width-responsive="true"></ins>`;
};

const pushAdsense = () => {
    (window.adsbygoogle = window.adsbygoogle || []).push({});
};

const isPlaceholderAdId = (value) => {
    const text = String(value || '').toUpperCase();
    return !text
        || text.includes('YOUR_CLIENT_ID')
        || text.includes('YOUR_AD_SLOT_ID')
        || text.includes('XXXXXXXX');
};

const consentKey = (cfg) => cfg?.consent_storage_key || CONSENT_KEY_FALLBACK;

const readConsent = (cfg) => {
    try {
        return String(localStorage.getItem(consentKey(cfg)) || '');
    } catch {
        return '';
    }
};

const writeConsent = (cfg, value) => {
    try {
        localStorage.setItem(consentKey(cfg), value);
    } catch {
        /* ignore */
    }
};

const isPersonalized = (cfg) => readConsent(cfg) === 'personalized';

const prefersKoreanDemand = () => {
    const htmlLang = String(document.documentElement.lang || '').toLowerCase();
    if (htmlLang.startsWith('ko')) return true;
    const nav = String(navigator.language || navigator.userLanguage || '').toLowerCase();
    return nav.startsWith('ko');
};

const slotFor = (cfg, placement) => {
    const fromPlacement = cfg.placements?.[placement]?.adsense_slot;
    if (placement === 'top') {
        return fromPlacement || cfg.adsense_slot_top || '';
    }
    if (placement === 'sidebar') {
        return fromPlacement || cfg.adsense_slot_sidebar || cfg.adsense_slot || '';
    }
    return '';
};

const adfitFor = (cfg, placement) => {
    if (placement === 'top') {
        return cfg.placements?.top?.adfit_unit || cfg.adfit_unit || '';
    }
    if (placement === 'sidebar') {
        return cfg.placements?.sidebar?.adfit_unit || cfg.adfit_unit_sidebar || '';
    }
    return '';
};

const applyFamilySafePolicy = (cfg) => {
    const rating = String(cfg.max_ad_content_rating || 'PG').toUpperCase();
    const safeRating = rating === 'G' || rating === 'PG' ? rating : 'PG';
    window.google_max_ad_content_rating = safeRating;
    window.google_tag_for_child_directed_treatment = cfg.tag_for_child_directed_treatment ? 1 : 0;
    window.google_tag_for_under_age_of_consent = cfg.tag_for_under_age_of_consent ? 1 : 0;
    window.adsbygoogle = window.adsbygoogle || [];
    window.adsbygoogle.requestNonPersonalizedAds = isPersonalized(cfg) ? 0 : 1;
};

const releaseAdRequests = () => {
    window.adsbygoogle = window.adsbygoogle || [];
    window.adsbygoogle.pauseAdRequests = 0;
};

const enableAutoAds = async (cfg) => {
    if (!cfg.auto_ads || !cfg.adsense_client || isPlaceholderAdId(cfg.adsense_client)) return;
    if (cfg.auto_ads_public_only && !document.body.classList.contains('public-page')) return;
    try {
        await loadAdsenseScript(cfg.adsense_client);
        window.adsbygoogle = window.adsbygoogle || [];
        window.adsbygoogle.push({
            google_ad_client: cfg.adsense_client,
            enable_page_level_ads: true,
            overlays: {
                bottom: Boolean(cfg.auto_ads_anchor),
                vignette: Boolean(cfg.auto_ads_vignette),
            },
        });
    } catch {
        /* Auto ads는 계정 설정에 의존. 실패해도 수동 유닛은 유지 */
    }
};

const watchAdFill = (container, ins, onEmpty) => {
    window.setTimeout(() => {
        if (!container.isConnected) return;
        const filled = ins.offsetHeight > 20 || Boolean(ins.querySelector('iframe'));
        container.classList.toggle('ad-container-filled', filled);
        container.classList.toggle('ad-container-empty', !filled);
        if (!filled && typeof onEmpty === 'function') onEmpty();
    }, 3500);
};

const openProFromAd = (cfg) => {
    if (cfg?.billing_enabled && cfg.checkout_plan) {
        window.location.href = `/pro/checkout?plan=${encodeURIComponent(cfg.checkout_plan)}`;
        return;
    }
    const proBtn = document.getElementById('openProBtn');
    if (proBtn) {
        proBtn.click();
        return;
    }
    window.location.href = '/login';
};

const houseAdAllowed = (ad, cfg) => {
    const blocked = new Set(
        [...(cfg.blocked_categories || []), ...ADULT_MARKS].map((c) => String(c).toLowerCase())
    );
    const cats = (ad.categories || []).map((c) => String(c).toLowerCase());
    return !cats.some((c) => blocked.has(c));
};

const pickHouseAd = (cfg) => {
    const inventory = (cfg.house_ads || []).filter((ad) => houseAdAllowed(ad, cfg));
    return inventory[0] || {
        id: 'pro_upgrade',
        categories: ['productivity', 'games'],
        title_key: 'ad.house_title',
        body_key: 'ad.house_body',
        cta_key: 'ad.card_open',
        image: 'city',
    };
};

const cityArtSvg = () => `
    <svg class="ad-card-art" viewBox="0 0 320 140" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
        <defs>
            <linearGradient id="adSky" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stop-color="#1d4ed8"/>
                <stop offset="100%" stop-color="#0f172a"/>
            </linearGradient>
        </defs>
        <rect width="320" height="140" fill="url(#adSky)"/>
        <rect x="18" y="58" width="36" height="82" fill="#334155"/>
        <rect x="62" y="38" width="44" height="102" fill="#1e293b"/>
        <rect x="116" y="70" width="32" height="70" fill="#475569"/>
        <rect x="160" y="28" width="52" height="112" fill="#1e3a5f"/>
        <rect x="222" y="52" width="40" height="88" fill="#334155"/>
        <rect x="270" y="64" width="34" height="76" fill="#1e293b"/>
        <rect x="0" y="118" width="320" height="22" fill="#0b1220"/>
        <rect x="24" y="124" width="272" height="6" fill="#64748b"/>
        <circle cx="86" cy="112" r="7" fill="#fbbf24"/>
        <circle cx="198" cy="112" r="7" fill="#38bdf8"/>
        <rect x="70" y="48" width="8" height="8" fill="#fde68a"/>
        <rect x="176" y="40" width="8" height="8" fill="#93c5fd"/>
        <rect x="188" y="56" width="8" height="8" fill="#fde68a"/>
    </svg>`;

const renderHouseBanner = (inner, cfg) => {
    inner.innerHTML = `
        <div class="top-ad-house">
            <span class="ad-label">${window.t('ad.top_label')}</span>
            <div class="top-ad-house-copy">
                <strong>${window.t('ad.house_title')}</strong>
                <span>${window.t('ad.house_body')}</span>
            </div>
            <button type="button" class="btn btn-premium btn-sm" id="topAdProBtn">${window.t('ad.house_cta')}</button>
            <em class="top-ad-safe">${window.t('ad.family_safe')}</em>
        </div>`;
    document.getElementById('topAdProBtn')?.addEventListener('click', () => openProFromAd(cfg));
};

const renderHouseCard = (slot, cfg) => {
    const ad = pickHouseAd(cfg);
    slot.hidden = false;
    slot.innerHTML = `
        <article class="ad-card" data-ad-safe="family" data-max-rating="${cfg.max_ad_content_rating || 'PG'}">
            <div class="ad-card-media">
                ${cityArtSvg()}
                <span class="ad-card-badge">${window.t('ad.top_label')}</span>
            </div>
            <h3 class="ad-card-title">${window.t(ad.title_key || 'ad.house_title')}</h3>
            <div class="ad-card-foot">
                <p class="ad-card-desc">${window.t(ad.body_key || 'ad.house_body')}</p>
                <button type="button" class="ad-card-cta" id="sideAdOpenBtn">${window.t(ad.cta_key || 'ad.card_open')}</button>
            </div>
        </article>`;
    document.getElementById('sideAdOpenBtn')?.addEventListener('click', () => openProFromAd(cfg));
};

const renderAdsenseUnit = async (host, cfg, slot, extraClass, onEmpty) => {
    const client = cfg.adsense_client;
    if (isPlaceholderAdId(client) || isPlaceholderAdId(slot)) {
        onEmpty();
        return;
    }
    host.innerHTML = displayAdIns(client, slot, extraClass);
    const ins = host.querySelector('ins.adsbygoogle');
    try {
        await loadAdsenseScript(client);
        pushAdsense();
        watchAdFill(host, ins, onEmpty);
    } catch {
        onEmpty();
    }
};

const renderAdfitUnit = async (host, cfg, unit, width, height, extraClass, onEmpty) => {
    if (isPlaceholderAdId(unit)) {
        onEmpty();
        return;
    }
    host.innerHTML = `
        <ins class="kakao_ad_area ${extraClass}"
            style="display:none;"
            data-ad-unit="${unit}"
            data-ad-width="${width}"
            data-ad-height="${height}"
            data-ad-safe="family"></ins>`;
    try {
        await loadScriptOnce('https://t1.daumcdn.net/kas/static/ba.min.js', 'adfit-loader');
        window.setTimeout(() => {
            const ins = host.querySelector('ins.kakao_ad_area');
            const filled = ins && (ins.offsetHeight > 20 || ins.querySelector('iframe'));
            if (!filled) onEmpty();
        }, 3500);
    } catch {
        onEmpty();
    }
};

const renderTop = (cfg) => {
    const inner = document.getElementById('topAdInner');
    if (!inner) return;
    const useAdfit = Boolean(cfg.korean_adfit_top) && prefersKoreanDemand() && !isPlaceholderAdId(adfitFor(cfg, 'top'));
    if (useAdfit) {
        renderAdfitUnit(inner, cfg, adfitFor(cfg, 'top'), 728, 90, 'top-ad-unit', () => {
            const adsenseSlot = slotFor(cfg, 'top');
            if (!isPlaceholderAdId(cfg.adsense_client) && !isPlaceholderAdId(adsenseSlot)) {
                renderAdsenseUnit(inner, cfg, adsenseSlot, 'top-ad-unit', () => renderHouseBanner(inner, cfg));
                return;
            }
            renderHouseBanner(inner, cfg);
        });
        return;
    }
    const adsenseSlot = slotFor(cfg, 'top');
    if (!isPlaceholderAdId(cfg.adsense_client) && !isPlaceholderAdId(adsenseSlot)) {
        renderAdsenseUnit(inner, cfg, adsenseSlot, 'top-ad-unit', () => renderHouseBanner(inner, cfg));
        return;
    }
    renderHouseBanner(inner, cfg);
};

const renderSidebar = (cfg) => {
    const container = document.getElementById('sidebarDisplayAd');
    if (!container) return;
    const houseFallback = () => {
        container.hidden = false;
        container.classList.remove('ad-container-empty');
        renderHouseCard(container, cfg);
    };
    const adsenseSlot = slotFor(cfg, 'sidebar');
    if (!isPlaceholderAdId(cfg.adsense_client) && !isPlaceholderAdId(adsenseSlot)) {
        container.hidden = false;
        container.classList.remove('ad-container-empty');
        renderAdsenseUnit(container, cfg, adsenseSlot, 'ad-sidebar-unit', houseFallback);
        return;
    }
    const adfit = adfitFor(cfg, 'sidebar');
    if (prefersKoreanDemand() && !isPlaceholderAdId(adfit)) {
        container.hidden = false;
        renderAdfitUnit(container, cfg, adfit, 300, 250, 'ad-card-unit', houseFallback);
        return;
    }
    houseFallback();
};

const renderCard = (cfg) => {
    const slot = document.getElementById('adSlot');
    if (!slot) return;
    renderHouseCard(slot, cfg);
};

const hasNetworkAds = (cfg) => (
    !isPlaceholderAdId(cfg.adsense_client)
    || !isPlaceholderAdId(adfitFor(cfg, 'top'))
    || !isPlaceholderAdId(adfitFor(cfg, 'sidebar'))
);

const bindConsent = (cfg, onReady) => {
    const bar = document.getElementById('adConsentBar');
    const existing = readConsent(cfg);
    if (existing || !hasNetworkAds(cfg)) {
        if (bar) bar.hidden = true;
        onReady();
        return;
    }
    if (bar) {
        bar.hidden = false;
        document.body.classList.add('has-ad-consent');
    }
    const finish = (value) => {
        writeConsent(cfg, value);
        applyFamilySafePolicy(cfg);
        if (bar) bar.hidden = true;
        document.body.classList.remove('has-ad-consent');
        onReady();
    };
    document.getElementById('adConsentPersonalized')?.addEventListener('click', () => finish('personalized'));
    document.getElementById('adConsentNpa')?.addEventListener('click', () => finish('npa'));
};

const fillNetwork = (cfg) => {
    applyFamilySafePolicy(cfg);
    releaseAdRequests();
    enableAutoAds(cfg);
    const bar = document.getElementById('topAdBar');
    const inner = document.getElementById('topAdInner');
    if (bar && !bar.hidden && inner && !window.cityflowAds._topFilled) {
        window.cityflowAds._topFilled = true;
        renderTop(cfg);
    }
    const sidebar = document.getElementById('sidebarDisplayAd');
    if (sidebar && !window.cityflowAds._sidebarFilled) {
        window.cityflowAds._sidebarFilled = true;
        renderSidebar(cfg);
    }
};

window.cityflowAds = {
    _topFilled: false,
    _cardFilled: false,
    _sidebarFilled: false,
    _booted: false,

    apply(player) {
        const cfg = window.CITYFLOW_ADS || {};
        applyFamilySafePolicy(cfg);
        const show = Boolean(player?.show_ads) && cfg.enabled !== false;
        const bar = document.getElementById('topAdBar');
        if (bar) {
            bar.hidden = !show;
            document.body.classList.toggle('has-top-ad', show);
        }
        const slot = document.getElementById('adSlot');
        if (slot) {
            slot.hidden = !show;
            if (show && !this._cardFilled) {
                this._cardFilled = true;
                renderCard(cfg);
            }
        }
        const sidebar = document.getElementById('sidebarDisplayAd');
        if (sidebar && !show) {
            sidebar.hidden = true;
        }
        const consentBar = document.getElementById('adConsentBar');
        if (!show) {
            if (consentBar) consentBar.hidden = true;
            document.body.classList.remove('has-ad-consent');
            return;
        }
        if (this._booted) return;
        this._booted = true;
        bindConsent(cfg, () => fillNetwork(cfg));
    },

    refreshHouse() {
        const cfg = window.CITYFLOW_ADS || {};
        const bar = document.getElementById('topAdBar');
        const inner = document.getElementById('topAdInner');
        if (bar && !bar.hidden && inner && inner.querySelector('.top-ad-house')) {
            renderHouseBanner(inner, cfg);
        }
        const slot = document.getElementById('adSlot');
        if (slot && !slot.hidden) renderHouseCard(slot, cfg);
    },
};

window.addEventListener('cityflow:lang', () => {
    window.cityflowAds?.refreshHouse();
});
