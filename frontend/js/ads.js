/** 최상단 배너. 성인·선정성 광고는 하우스 인벤토리에서 배제합니다. */

const loadScriptOnce = (src, id) => new Promise((resolve, reject) => {
    if (id && document.getElementById(id)) {
        resolve();
        return;
    }
    const el = document.createElement('script');
    if (id) el.id = id;
    el.async = true;
    el.src = src;
    el.onload = () => resolve();
    el.onerror = () => reject(new Error('ad script failed'));
    document.head.appendChild(el);
});

const openProFromAd = (cfg) => {
    if (cfg?.billing_enabled && cfg.checkout_plan) {
        window.location.href = `/pro/checkout?plan=${encodeURIComponent(cfg.checkout_plan)}`;
        return;
    }
    document.getElementById('openProBtn')?.click();
};

const renderHouse = (inner, cfg) => {
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

const renderAdsense = async (inner, cfg) => {
    inner.innerHTML = `
        <ins class="adsbygoogle top-ad-unit"
            style="display:block;width:100%;max-width:728px;height:90px"
            data-ad-client="${cfg.adsense_client}"
            data-ad-slot="${cfg.adsense_slot}"
            data-ad-format="horizontal"
            data-full-width-responsive="false"></ins>`;
    const src = `https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=${encodeURIComponent(cfg.adsense_client)}`;
    try {
        await loadScriptOnce(src, 'adsense-loader');
        window.adsbygoogle = window.adsbygoogle || [];
        window.adsbygoogle.push({});
    } catch {
        renderHouse(inner, cfg);
    }
};

const renderAdfit = async (inner, cfg) => {
    inner.innerHTML = `
        <ins class="kakao_ad_area top-ad-unit"
            style="display:none;"
            data-ad-unit="${cfg.adfit_unit}"
            data-ad-width="728"
            data-ad-height="90"></ins>`;
    try {
        await loadScriptOnce('https://t1.daumcdn.net/kas/static/ba.min.js', 'adfit-loader');
    } catch {
        renderHouse(inner, cfg);
    }
};

window.cityflowAds = {
    _filled: false,

    apply(player) {
        const bar = document.getElementById('topAdBar');
        if (!bar) return;
        const cfg = window.CITYFLOW_ADS || {};
        const show = Boolean(player?.show_ads) && cfg.enabled !== false;
        bar.hidden = !show;
        document.body.classList.toggle('has-top-ad', show);
        if (show && !this._filled) {
            this._filled = true;
            this.render(cfg);
        }
    },

    render(cfg) {
        const inner = document.getElementById('topAdInner');
        if (!inner) return;
        if (cfg.provider === 'adsense' && cfg.adsense_client && cfg.adsense_slot) {
            renderAdsense(inner, cfg);
            return;
        }
        if (cfg.provider === 'adfit' && cfg.adfit_unit) {
            renderAdfit(inner, cfg);
            return;
        }
        renderHouse(inner, cfg);
    },
};

window.addEventListener('cityflow:lang', () => {
    const cfg = window.CITYFLOW_ADS || {};
    const bar = document.getElementById('topAdBar');
    if (!bar || bar.hidden) return;
    if (cfg.provider && cfg.provider !== 'house') return;
    const inner = document.getElementById('topAdInner');
    if (inner) renderHouse(inner, cfg);
});
