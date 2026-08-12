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
        data = { ok: false, message: '서버 응답을 해석할 수 없습니다.' };
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
        if (streakEl) streakEl.textContent = `${player.streak_days}일`;
        if (xpFill && player.xp_to_next) {
            const pct = Math.min(100, (player.xp / player.xp_to_next) * 100);
            xpFill.style.width = `${pct}%`;
        }
        if (proBadge) {
            proBadge.hidden = !player.is_pro;
            proBadge.textContent = player.is_pro ? 'PRO' : '';
        }

        const adSlot = document.getElementById('adSlot');
        if (adSlot) adSlot.hidden = !player.show_ads;

        const exportBtn = document.getElementById('exportAnalyticsBtn');
        if (exportBtn) {
            exportBtn.classList.toggle('pro-gated', !player.is_pro);
            exportBtn.dataset.proOnly = player.is_pro ? '0' : '1';
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
                        <strong>${s.name}</strong>
                        <span class="stage-diff">★${s.difficulty}</span>
                    </div>
                    <p class="quest-desc">${s.description}</p>
                    <button type="button" class="btn btn-secondary btn-sm stage-start-btn" data-stage-id="${s.id}"
                        ${s.completed ? 'disabled' : ''}>
                        ${s.completed ? '클리어' : (s.active ? '진행 중' : '시작')}
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
            list.innerHTML = '<li class="event-empty">스테이지 로드 실패</li>';
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
                `<li>${g.completed ? '✓' : '○'} ${g.label}: ${Math.floor(g.progress)}/${g.target}</li>`
            ).join('');
            activeEl.innerHTML = `
                <strong>${stage.name}</strong>
                <ul class="stage-goals">${goals}</ul>
                <button type="button" class="btn btn-premium btn-sm" id="claimStageBtn"
                    ${stage.all_goals_met && !stage.completed ? '' : 'disabled'}>
                    ${stage.completed ? '이미 클리어' : '클리어 보상 받기'}
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
            list.innerHTML = '<li class="event-empty">퀘스트 로딩 중…</li>';
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
                btn = `<button type="button" class="quest-claim-btn" data-quest-id="${q.id}">보상</button>`;
            } else if (claimed) {
                btn = '<span class="quest-done">✓</span>';
            }
            return `
                <li class="quest-item${done ? ' done' : ''}">
                    <div class="quest-head">
                        <strong>${q.label}</strong>${btn}
                    </div>
                    <p class="quest-desc">${q.description}</p>
                    <div class="quest-bar"><div class="quest-fill" style="width:${pct}%"></div></div>
                    <span class="quest-reward">🪙${q.reward_coins} · XP ${q.reward_xp}</span>
                </li>`;
        }).join('');

        const bonusBtn = document.getElementById('claimDailyBonusBtn');
        if (bonusBtn) {
            const allDone = quests.every((q) => q.completed);
            const bonusClaimed = player.daily?.all_complete_bonus_claimed;
            bonusBtn.disabled = !allDone || bonusClaimed;
            bonusBtn.textContent = bonusClaimed ? '오늘 보너스 수령함' : '일일 올클리어 보너스 (+100🪙)';
        }
    },

    renderAchievements(player) {
        const el = document.getElementById('achievementList');
        if (!el) return;
        const unlocked = new Set(player.achievements || []);
        const catalog = player.achievement_catalog || [];
        if (!catalog.length) {
            el.innerHTML = '<li class="event-empty">업적 정보 없음</li>';
            return;
        }
        el.innerHTML = catalog.map((a) => {
            const done = unlocked.has(a.id);
            const title = a.label || a.name || a.id;
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
                ? `슬롯 ${i + 1}: ${meta.name}`
                : `슬롯 ${i + 1} (비어 있음)`;
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
            { id: 'default', name: '기본' },
            { id: 'neon', name: '네온' },
            { id: 'sunset', name: '선셋' },
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
                    <li>${i + 1}. ${r.login_id} · Lv.${r.level} · 주간 XP ${Math.round(r.weekly_xp)}</li>`).join('')
                : '<li class="event-empty">아직 참가자가 없습니다</li>';
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
                <h4>${item.name}</h4>
                <p>${item.description}</p>
                <button type="button" class="btn btn-secondary shop-buy-btn" data-item-id="${item.id}"
                    ${already && item.type === 'cosmetic' ? 'disabled' : ''}>
                    ${already && item.type === 'cosmetic' ? '보유 중' : `🪙 ${item.price_coins}`}
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

        document.getElementById('openProBtn')?.addEventListener('click', () => openModal('proModal'));
        document.getElementById('openProBtnAd')?.addEventListener('click', () => openModal('proModal'));
        document.getElementById('closeProBtn')?.addEventListener('click', () => closeModal('proModal'));
        document.getElementById('activateProDemoBtn')?.addEventListener('click', async () => {
            const data = await apiPost('/api/engagement/pro/activate-demo');
            window.uiBridge?.showToast(data.message, data.ok ? 'info' : 'warning');
            if (data.player) {
                this._savesMeta = null;
                this.applyPlayer(data.player);
            }
            closeModal('proModal');
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
                window.uiBridge?.showToast('CSV 내보내기는 PRO 기능입니다. PRO를 체험해 보세요.', 'warning');
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
