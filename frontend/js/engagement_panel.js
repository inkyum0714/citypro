/** 재방문·수익화 UI: 퀘스트, 상점, PRO, 저장, 리더보드 */

const apiPost = async (url, body = {}) => {
    const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });
    let data = {};
    try {
        data = await res.json();
    } catch {
        data = { ok: false, message: window.t('login.parse') };
    }
    return data;
};

const applyCosmeticTheme = (cosmetic) => {
    document.body.dataset.cosmetic = cosmetic || 'default';
};

const closeModal = (id) => {
    document.getElementById(id)?.classList.remove('open');
};

const openModal = (id) => {
    document.getElementById(id)?.classList.add('open');
};

window.engagementPanel = {
    player: null,
    _leaderboardLoaded: false,
    _leaderboardTimer: null,
    _questsBound: false,
    _savesMeta: null,
    _stagesLoaded: false,

    update(state) {
        const player = state.player;
        if (!player) return;
        this.player = player;
        applyCosmeticTheme(player.active_cosmetic);

        const levelEl = document.getElementById('playerLevel');
        const xpFill = document.getElementById('playerXpFill');
        const coinsEl = document.getElementById('playerCoins');
        const streakEl = document.getElementById('playerStreak');
        const proBadge = document.getElementById('proBadge');

        if (levelEl) levelEl.textContent = `Lv.${player.level}`;
        if (coinsEl) coinsEl.textContent = String(player.coins);
        if (streakEl) streakEl.textContent = window.t('player.streak', { n: player.streak_days });
        if (xpFill && player.xp_to_next) {
            const pct = Math.min(100, (player.xp / player.xp_to_next) * 100);
            xpFill.style.width = `${pct}%`;
        }
        if (proBadge) {
            proBadge.hidden = !player.is_pro;
            proBadge.textContent = player.plan_label || (player.is_pro ? 'PRO' : '');
        }

        const adSlot = document.getElementById('adSlot');
        if (adSlot) adSlot.hidden = !player.show_ads;
        window.cityflowAds?.apply(player);

        const exportBtn = document.getElementById('exportAnalyticsBtn');
        if (exportBtn) {
            exportBtn.classList.toggle('pro-gated', !player.is_pro);
            exportBtn.dataset.proOnly = player.is_pro ? '0' : '1';
        }

        this.noticeTrialExpired(player);
        const expEl = document.getElementById('couponExpiredMsg');
        if (expEl) {
            expEl.hidden = !player.trial_expired;
            if (player.trial_expired) expEl.textContent = window.t('coupon.trial_expired');
        }

        this.renderDailyQuests(player);
        this.renderAchievements(player);
        this.syncSaveSlots(player);
        this.renderCosmeticPicker(player);
        if (!this._stagesLoaded) {
            this.renderStages(player);
        }
        if (!this._leaderboardLoaded) {
            this.renderLeaderboardPreview();
        }
    },

    noticeTrialExpired(player) {
        if (!player?.trial_expired) return;
        const key = `trialExpired:${player.login_id}:${player.trial_ended_at || ''}`;
        try {
            if (sessionStorage.getItem(key) === '1') return;
            sessionStorage.setItem(key, '1');
        } catch {
            /* ignore */
        }
        window.uiBridge?.showToast(window.t('coupon.trial_expired'), 'warning');
    },

    applyPlayer(player) {
        if (player) this.update({ player });
    },

    async renderStages(player) {
        const list = document.getElementById('stageList');
        const activeEl = document.getElementById('stageActive');
        if (!list) return;
        try {
            const res = await fetch('/api/engagement/stages');
            const data = await res.json();
            if (!data.ok) return;
            const stages = data.stages || [];
            list.innerHTML = stages.map((s) => `
                <li class="stage-item${s.completed ? ' done' : ''}${s.active ? ' active' : ''}">
                    <div class="stage-head">
                        <strong>${window.t(`stage.${s.id}.name`, s.name)}</strong>
                        <span class="stage-diff">★${s.difficulty}</span>
                    </div>
                    <p class="quest-desc">${window.t(`stage.${s.id}.desc`, s.description)}</p>
                    <button type="button" class="btn btn-secondary btn-sm stage-start-btn" data-stage-id="${s.id}"
                        ${s.completed ? 'disabled' : ''}>
                        ${s.completed ? window.t('stage.clear') : (s.active ? window.t('stage.active') : window.t('stage.start'))}
                    </button>
                </li>`).join('');
            list.querySelectorAll('.stage-start-btn').forEach((btn) => {
                btn.addEventListener('click', async () => {
                    const data2 = await apiPost('/api/engagement/stages/start', { stage_id: btn.dataset.stageId });
                    window.uiBridge?.showToast(data2.message, data2.ok ? 'info' : 'warning');
                    if (data2.player) this.applyPlayer(data2.player);
                    if (data2.ok) {
                        this._stagesLoaded = false;
                        window.uiBridge?.refreshSimulationState?.();
                        await this.renderStages(data2.player);
                    }
                });
            });
            this._stagesLoaded = true;
            this.refreshStageStatus();
        } catch {
            list.innerHTML = `<li class="event-empty">${window.t('stage.load_fail')}</li>`;
        }
    },

    async refreshStageStatus() {
        const activeEl = document.getElementById('stageActive');
        if (!activeEl) return;
        try {
            const res = await fetch('/api/engagement/stages/status');
            const data = await res.json();
            const stage = data.stage;
            if (!stage || !stage.id) {
                activeEl.hidden = true;
                return;
            }
            activeEl.hidden = false;
            const goals = (stage.goals || []).map((g) =>
                `<li>${g.completed ? '✓' : '○'} ${window.t(`goal.${g.metric}`, { n: g.target }, g.label)}: ${Math.floor(g.progress)}/${g.target}</li>`
            ).join('');
            activeEl.innerHTML = `
                <strong>${window.t(`stage.${stage.id}.name`, stage.name)}</strong>
                <ul class="stage-goals">${goals}</ul>
                <button type="button" class="btn btn-premium btn-sm" id="claimStageBtn"
                    ${stage.all_goals_met && !stage.completed ? '' : 'disabled'}>
                    ${stage.completed ? window.t('stage.already') : window.t('stage.claim')}
                </button>`;
            document.getElementById('claimStageBtn')?.addEventListener('click', async () => {
                const data2 = await apiPost('/api/engagement/stages/claim', { stage_id: stage.id });
                window.uiBridge?.showToast(data2.message, data2.ok ? 'info' : 'warning');
                if (data2.player) this.applyPlayer(data2.player);
                this.refreshStageStatus();
            });
        } catch {
            activeEl.hidden = true;
        }
    },

    updateFromState(state) {
        if (state?.stage?.id) {
            this.refreshStageStatus();
        }
    },

    renderDailyQuests(player) {
        const list = document.getElementById('dailyQuestList');
        if (!list) return;
        const quests = player.daily?.quests || [];
        if (!quests.length) {
            list.innerHTML = `<li class="event-empty">${window.t('quest.loading')}</li>`;
            return;
        }
        list.innerHTML = quests.map((q) => {
            const target = Number(q.target) || 1;
            const progress = Number(q.progress) || 0;
            const pct = Math.min(100, (progress / target) * 100);
            const done = q.completed;
            const claimed = q.claimed;
            let btn = '';
            if (done && !claimed) {
                btn = `<button type="button" class="quest-claim-btn" data-quest-id="${q.id}">${window.t('quest.claim')}</button>`;
            } else if (claimed) {
                btn = '<span class="quest-done">✓</span>';
            }
            return `
                <li class="quest-item${done ? ' done' : ''}">
                    <div class="quest-head">
                        <strong>${window.t(`quest.${q.id}.label`, q.label)}</strong>${btn}
                    </div>
                    <p class="quest-desc">${window.t(`quest.${q.id}.desc`, q.description)}</p>
                    <div class="quest-bar"><div class="quest-fill" style="width:${pct}%"></div></div>
                    <span class="quest-reward">🪙${q.reward_coins} · XP ${q.reward_xp}</span>
                </li>`;
        }).join('');

        const bonusBtn = document.getElementById('claimDailyBonusBtn');
        if (bonusBtn) {
            const allDone = quests.every((q) => q.completed);
            const bonusClaimed = player.daily?.all_complete_bonus_claimed;
            bonusBtn.disabled = !allDone || bonusClaimed;
            bonusBtn.textContent = bonusClaimed ? window.t('quest.bonus_claimed') : window.t('quest.bonus');
        }
    },

    renderAchievements(player) {
        const el = document.getElementById('achievementList');
        if (!el) return;
        const unlocked = new Set(player.achievements || []);
        const catalog = player.achievement_catalog || [];
        if (!catalog.length) {
            el.innerHTML = `<li class="event-empty">${window.t('ach.empty')}</li>`;
            return;
        }
        el.innerHTML = catalog.map((a) => {
            const done = unlocked.has(a.id);
            const title = window.t(`ach.${a.id}`, a.label || a.name || a.id);
            return `<li class="achievement-item${done ? ' unlocked' : ''}">${done ? '🏅' : '🔒'} ${title}</li>`;
        }).join('');
    },

    async syncSaveSlots(player) {
        const select = document.getElementById('saveSlotSelect');
        if (!select) return;
        const slots = Math.max(1, Number(player.save_slots) || 1);
        const prev = select.value;
        if (!this._savesMeta) {
            try {
                const res = await fetch('/api/engagement/saves');
                const data = await res.json();
                if (data.ok) this._savesMeta = data.saves || {};
            } catch {
                this._savesMeta = {};
            }
        }
        const saves = this._savesMeta || {};
        select.innerHTML = '';
        for (let i = 0; i < slots; i += 1) {
            const opt = document.createElement('option');
            opt.value = String(i);
            const meta = saves[String(i)];
            opt.textContent = meta?.name
                ? window.t('save.slot_named', { n: i + 1, name: meta.name })
                : window.t('save.slot_empty', { n: i + 1 });
            select.appendChild(opt);
        }
        if ([...select.options].some((o) => o.value === prev)) {
            select.value = prev;
        }
    },

    renderCosmeticPicker(player) {
        const el = document.getElementById('cosmeticPicker');
        if (!el) return;
        const owned = new Set(['default', ...(player.owned_items || [])]);
        const options = [
            { id: 'default', name: window.t('cosmetic.default') },
            { id: 'neon', name: window.t('cosmetic.neon') },
            { id: 'sunset', name: window.t('cosmetic.sunset') },
        ].filter((o) => owned.has(o.id) || o.id === 'default');
        el.innerHTML = options.map((o) => `
            <button type="button" class="cosmetic-btn${player.active_cosmetic === o.id ? ' active' : ''}"
                data-cosmetic-id="${o.id}">${o.name}</button>
        `).join('');
        el.querySelectorAll('.cosmetic-btn').forEach((btn) => {
            btn.addEventListener('click', async () => {
                const data = await apiPost('/api/engagement/cosmetic', {
                    cosmetic_id: btn.dataset.cosmeticId,
                });
                if (data.player) this.applyPlayer(data.player);
            });
        });
    },

    async renderLeaderboardPreview() {
        const el = document.getElementById('leaderboardPreview');
        if (!el) return;
        try {
            const res = await fetch('/api/engagement/leaderboard');
            const data = await res.json();
            if (!data.ok) return;
            this._leaderboardLoaded = true;
            const rows = (data.leaderboard || []).slice(0, 5);
            el.innerHTML = rows.length
                ? rows.map((r, i) => `
                    <li>${i + 1}. ${r.login_id} · Lv.${r.level} · ${window.t('lb.weekly', { n: Math.round(r.weekly_xp) })}</li>`).join('')
                : `<li class="event-empty">${window.t('lb.empty')}</li>`;
        } catch {
            /* ignore */
        }
    },

    renderShop(player) {
        const grid = document.getElementById('shopGrid');
        if (!grid) return;
        const items = player.shop || [];
        const owned = new Set(player.owned_items || []);
        grid.innerHTML = items.map((item) => {
            const cosmeticId = item.cosmetic_id;
            const already = (cosmeticId && owned.has(cosmeticId))
                || (item.type === 'save_slot' && owned.has(item.id))
                || owned.has(item.id);
            return `
            <div class="shop-card${already ? ' owned' : ''}">
                <h4>${window.t(`shop.${item.id}.name`, item.name)}</h4>
                <p>${window.t(`shop.${item.id}.desc`, item.description)}</p>
                <button type="button" class="btn btn-secondary shop-buy-btn" data-item-id="${item.id}"
                    ${already && item.type === 'cosmetic' ? 'disabled' : ''}>
                    ${already && item.type === 'cosmetic' ? window.t('shop.owned') : `🪙 ${item.price_coins}`}
                </button>
            </div>`;
        }).join('');
        grid.querySelectorAll('.shop-buy-btn').forEach((btn) => {
            btn.addEventListener('click', async () => {
                const data = await apiPost('/api/engagement/shop/buy', { item_id: btn.dataset.itemId });
                window.uiBridge?.showToast(data.message, data.ok ? 'info' : 'warning');
                if (data.player) {
                    this._savesMeta = null;
                    this.applyPlayer(data.player);
                    this.renderShop(data.player);
                }
            });
        });
    },

    renderPlans(player) {
        const grid = document.getElementById('planGrid');
        if (!grid) return;
        const plans = player.plans || [];
        const billingOn = Boolean(player.billing_enabled);
        const current = player.plan || 'free';
        grid.innerHTML = plans.map((plan) => {
            const currentMark = current === plan.id ? `<span class="plan-current">${window.t('pro.current')}</span>` : '';
            const benefits = (plan.benefits || []).map((b, i) =>
                `<li>${window.t(`plan.${plan.id}.b${i}`, b)}</li>`
            ).join('');
            const price = window.t('plan.price_usd', { usd: plan.price_usd });
            const payLabel = billingOn ? window.t('pro.pay', { price }) : window.t('pro.pay_setup');
            return `
            <div class="plan-card${current === plan.id ? ' current' : ''}">
                <h4>${plan.name} ${currentMark}</h4>
                <p class="pro-price">${price} <span>${window.t('plan.price_krw', { krw: Number(plan.price_krw).toLocaleString() })} · ${window.t('pro.toss')}</span></p>
                <ul class="pro-benefits">${benefits}</ul>
                <button type="button" class="btn btn-premium full-width plan-pay-btn" data-plan-id="${plan.id}"
                    ${billingOn ? '' : 'disabled'}>
                    ${payLabel}
                </button>
            </div>`;
        }).join('');
        grid.querySelectorAll('.plan-pay-btn').forEach((btn) => {
            btn.addEventListener('click', () => {
                window.location.href = `/pro/checkout?plan=${encodeURIComponent(btn.dataset.planId)}`;
            });
        });
    },

    bind() {
        const questList = document.getElementById('dailyQuestList');
        if (questList && !this._questsBound) {
            this._questsBound = true;
            questList.addEventListener('click', async (ev) => {
                const btn = ev.target.closest('.quest-claim-btn');
                if (!btn) return;
                const data = await apiPost('/api/engagement/claim-quest', {
                    quest_id: btn.dataset.questId,
                });
                window.uiBridge?.showToast(data.message, data.ok ? 'info' : 'warning');
                if (data.player) this.applyPlayer(data.player);
            });
        }

        document.getElementById('claimDailyBonusBtn')?.addEventListener('click', async () => {
            const data = await apiPost('/api/engagement/claim-daily-bonus');
            window.uiBridge?.showToast(data.message, data.ok ? 'info' : 'warning');
            if (data.player) this.applyPlayer(data.player);
        });

        document.getElementById('openShopBtn')?.addEventListener('click', () => {
            if (this.player) this.renderShop(this.player);
            openModal('shopModal');
        });
        document.getElementById('closeShopBtn')?.addEventListener('click', () => closeModal('shopModal'));

        document.getElementById('openProBtn')?.addEventListener('click', () => {
            if (this.player) this.renderPlans(this.player);
            openModal('proModal');
        });
        document.getElementById('openProBtnAd')?.addEventListener('click', () => {
            if (this.player) this.renderPlans(this.player);
            openModal('proModal');
        });
        document.getElementById('closeProBtn')?.addEventListener('click', () => closeModal('proModal'));
        document.getElementById('redeemCouponBtn')?.addEventListener('click', async () => {
            const input = document.getElementById('couponCodeInput');
            const code = (input?.value || '').trim();
            const data = await apiPost('/api/engagement/coupon/redeem', { code });
            window.uiBridge?.showToast(data.message, data.ok ? 'info' : 'warning');
            if (data.player) {
                this._savesMeta = null;
                this.applyPlayer(data.player);
                this.renderPlans(data.player);
            }
            if (data.ok) closeModal('proModal');
        });

        document.querySelectorAll('.modal').forEach((modal) => {
            modal.addEventListener('click', (ev) => {
                if (ev.target === modal) modal.classList.remove('open');
            });
        });
        document.addEventListener('keydown', (ev) => {
            if (ev.key === 'Escape') {
                closeModal('shopModal');
                closeModal('proModal');
            }
        });

        document.getElementById('saveCityBtn')?.addEventListener('click', async () => {
            const slot = Number(document.getElementById('saveSlotSelect')?.value || 0);
            const name = document.getElementById('saveCityName')?.value || '';
            const data = await apiPost('/api/engagement/saves', { slot, name });
            window.uiBridge?.showToast(data.message, data.ok ? 'info' : 'warning');
            if (data.player) {
                this._savesMeta = null;
                this.applyPlayer(data.player);
            }
        });

        document.getElementById('loadCityBtn')?.addEventListener('click', async () => {
            const slot = Number(document.getElementById('saveSlotSelect')?.value || 0);
            const data = await apiPost('/api/engagement/saves/load', { slot });
            window.uiBridge?.showToast(data.message, data.ok ? 'info' : 'warning');
            if (data.ok) {
                window.uiBridge?.refreshSimulationState();
            }
        });

        document.getElementById('exportAnalyticsBtn')?.addEventListener('click', (e) => {
            if (e.currentTarget.dataset.proOnly === '1') {
                e.preventDefault();
                window.uiBridge?.showToast(window.t('toast.csv_pro'), 'warning');
                openModal('proModal');
            }
        });

        fetch('/api/engagement/me')
            .then((r) => r.json())
            .then((data) => {
                if (data.ok && data.player) this.applyPlayer(data.player);
            })
            .catch(() => {});

        this._leaderboardTimer = window.setInterval(() => {
            this._leaderboardLoaded = false;
            this.renderLeaderboardPreview();
        }, 60000);

        window.setInterval(() => this.refreshStageStatus(), 4000);
    },
};

window.engagementPanel.bind();
