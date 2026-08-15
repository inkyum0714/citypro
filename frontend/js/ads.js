/** 사이드바 카드·상단 배너. 성인·선정성 광고는 하우스·네트워크 모두에서 배제합니다. */

const ADULT_MARKS = ['adult', 'sexual', 'dating', 'pornography'];

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

/** Google AdSense Display Ads 공식 스니펫과 동일한 유닛 마크업. */
const displayAdIns = (cfg, extraClass = '') => {
    const cls = extraClass ? `adsbygoogle ${extraClass}` : 'adsbygoogle';
    return `
    <!-- Display Ads -->
    <ins class="${cls}"
         style="display:block"
         data-ad-client="${cfg.adsense_client}"
         data-ad-slot="${cfg.adsense_slot}"
         data-ad-format="auto"
         data-full-width-responsive="true"></ins>`;
};

const pushAdsense = () => {
    (window.adsbygoogle = window.adsbygoogle || []).push({});
};

const pickRandomSlot = (cfg) => {
    const slots = (cfg.adsense_slots || []).filter(Boolean);
    if (slots.length) {
        return slots[Math.floor(Math.random() * slots.length)];
    }
    return cfg.adsense_slot || '';
};

const isPlaceholderAdId = (value) => {
    const text = String(value || '').toUpperCase();
    return !text
        || text.includes('YOUR_CLIENT_ID')
        || text.includes('YOUR_AD_SLOT_ID')
        || text.includes('XXXXXXXX');
};

const watchAdFill = (container, ins) => {
    window.setTimeout(() => {
        if (!container.isConnected) return;
        const filled = ins.offsetHeight > 20 || Boolean(ins.querySelector('iframe'));
        container.classList.toggle('ad-container-filled', filled);
        container.classList.toggle('ad-container-empty', !filled);
        if (!filled) container.hidden = true;
    }, 3500);
};

const renderSidebarDisplay = async (cfg) => {
    const container = document.getElementById('sidebarDisplayAd');
    if (!container) return;
    const ins = container.querySelector('ins.adsbygoogle');
    const client = cfg.adsense_client;
    const slot = pickRandomSlot(cfg);
    if (!ins || isPlaceholderAdId(client) || isPlaceholderAdId(slot)) {
        container.hidden = true;
        container.classList.add('ad-container-empty');
        return;
    }
    ins.setAttribute('data-ad-client', client);
    ins.setAttribute('data-ad-slot', slot);
    ins.setAttribute('data-ad-format', 'auto');
    ins.setAttribute('data-full-width-responsive', 'true');
    ins.style.display = 'block';
    container.hidden = false;
    container.classList.remove('ad-container-empty');
    try {
        await loadAdsenseScript(client);
        pushAdsense();
        watchAdFill(container, ins);
    } catch {
        container.hidden = true;
        container.classList.add('ad-container-empty');
    }
};

const openProFromAd = (cfg) => {
    if (cfg?.billing_enabled && cfg.checkout_plan) {
        window.location.href = `/pro/checkout?plan=${encodeURIComponent(cfg.checkout_plan)}`;
        return;
    }
    document.getElementById('openProBtn')?.click();
};

const applyFamilySafePolicy = (cfg) => {
    const rating = String(cfg.max_ad_content_rating || 'PG').toUpperCase();
    const safeRating = rating === 'G' || rating === 'PG' ? rating : 'PG';
    window.google_max_ad_content_rating = safeRating;
    window.google_tag_for_child_directed_treatment = cfg.tag_for_child_directed_treatment ? 1 : 0;
    window.google_tag_for_under_age_of_consent = cfg.tag_for_under_age_of_consent ? 1 : 0;
    window.adsbygoogle = window.adsbygoogle || [];
    window.adsbygoogle.requestNonPersonalizedAds = 1;
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

const renderAdsenseBanner = async (inner, cfg) => {
    inner.innerHTML = displayAdIns(cfg, 'top-ad-unit');
    try {
        await loadAdsenseScript(cfg.adsense_client);
        pushAdsense();
    } catch {
        renderHouseBanner(inner, cfg);
    }
};

const renderAdsenseCard = async (slot, cfg) => {
    slot.innerHTML = `
        <article class="ad-card ad-card-network" data-ad-safe="family">
            <div class="ad-card-media">${displayAdIns(cfg, 'ad-card-unit')}</div>
        </article>`;
    try {
        await loadAdsenseScript(cfg.adsense_client);
        pushAdsense();
    } catch {
        renderHouseCard(slot, cfg);
    }
};

const renderAdfitBanner = async (inner, cfg) => {
    inner.innerHTML = `
        <ins class="kakao_ad_area top-ad-unit"
            style="display:none;"
            data-ad-unit="${cfg.adfit_unit}"
            data-ad-width="728"
            data-ad-height="90"
            data-ad-safe="family"></ins>`;
    try {
        await loadScriptOnce('https://t1.daumcdn.net/kas/static/ba.min.js', 'adfit-loader');
    } catch {
        renderHouseBanner(inner, cfg);
    }
};

const renderAdfitCard = async (slot, cfg) => {
    slot.innerHTML = `
        <article class="ad-card ad-card-network" data-ad-safe="family">
            <div class="ad-card-media">
                <ins class="kakao_ad_area ad-card-unit"
                    style="display:none;"
                    data-ad-unit="${cfg.adfit_unit}"
                    data-ad-width="300"
                    data-ad-height="250"
                    data-ad-safe="family"></ins>
            </div>
        </article>`;
    try {
        await loadScriptOnce('https://t1.daumcdn.net/kas/static/ba.min.js', 'adfit-loader');
    } catch {
        renderHouseCard(slot, cfg);
    }
};

window.cityflowAds = {
    _topFilled: false,
    _cardFilled: false,
    _sidebarFilled: false,

    apply(player) {
        const cfg = window.CITYFLOW_ADS || {};
        applyFamilySafePolicy(cfg);
        const show = Boolean(player?.show_ads) && cfg.enabled !== false;
        const bar = document.getElementById('topAdBar');
        if (bar) {
            bar.hidden = !show;
            document.body.classList.toggle('has-top-ad', show);
            if (show && !this._topFilled) {
                this._topFilled = true;
                this.renderTop(cfg);
            }
        }
        const slot = document.getElementById('adSlot');
        if (slot) {
            slot.hidden = !show;
            if (show && !this._cardFilled) {
                this._cardFilled = true;
                this.renderCard(cfg);
            }
        }
        const sidebar = document.getElementById('sidebarDisplayAd');
        if (sidebar) {
            if (!show) {
                sidebar.hidden = true;
            } else if (!this._sidebarFilled) {
                this._sidebarFilled = true;
                this.renderSidebar(cfg);
            }
        }
    },

    renderSidebar(cfg) {
        renderSidebarDisplay(cfg);
    },

    renderTop(cfg) {
        const inner = document.getElementById('topAdInner');
        if (!inner) return;
        if (cfg.provider === 'adsense' && cfg.adsense_client && cfg.adsense_slot) {
            renderAdsenseBanner(inner, cfg);
            return;
        }
        if (cfg.provider === 'adfit' && cfg.adfit_unit) {
            renderAdfitBanner(inner, cfg);
            return;
        }
        renderHouseBanner(inner, cfg);
    },

    renderCard(cfg) {
        const slot = document.getElementById('adSlot');
        if (!slot) return;
        if (cfg.provider === 'adsense' && cfg.adsense_client && cfg.adsense_slot) {
            renderAdsenseCard(slot, cfg);
            return;
        }
        if (cfg.provider === 'adfit' && cfg.adfit_unit) {
            renderAdfitCard(slot, cfg);
            return;
        }
        renderHouseCard(slot, cfg);
    },

    refreshHouse() {
        const cfg = window.CITYFLOW_ADS || {};
        if (cfg.provider && cfg.provider !== 'house') return;
        const bar = document.getElementById('topAdBar');
        const inner = document.getElementById('topAdInner');
        if (bar && !bar.hidden && inner) renderHouseBanner(inner, cfg);
        const slot = document.getElementById('adSlot');
        if (slot && !slot.hidden) renderHouseCard(slot, cfg);
    },
};

window.addEventListener('cityflow:lang', () => {
    window.cityflowAds?.refreshHouse();
});
