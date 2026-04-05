'use strict';

const AIGITO = {
    companySlug: null,
    state: 'idle', // idle | connecting | listening | thinking | speaking | error
    reconnectTimer: null,
    idleTimer: null,
    idleTimeout: 15000,
    demoMode: false,
    demoRemainingSeconds: null,
    demoTimer: null,
    demoStartTime: null,
    videoQuality: 'auto',
    selectedLanguage: 'ru',

    async init() {
        const parts = window.location.pathname.split('/').filter(Boolean);
        this.companySlug = parts[parts.length - 1] || 'demo';

        try {
            const config = await this.loadConfig();
            this.applyConfig(config);
        } catch (e) {
            console.warn('Could not load company config:', e);
        }

        document.getElementById('btn-start').addEventListener('click', () => this.startDialog());
        document.getElementById('btn-end').addEventListener('click', () => this.endDialog());
        document.getElementById('btn-mic').addEventListener('click', () => this.toggleMic());

        // Language selector
        document.querySelectorAll('.lang-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.lang-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this.selectedLanguage = btn.dataset.lang;
            });
        });

        // Fullscreen toggle
        const btnFs = document.getElementById('btn-fullscreen');
        if (btnFs) {
            btnFs.addEventListener('click', () => this._toggleFullscreen());
            document.addEventListener('fullscreenchange', () => this._updateFullscreenIcon());
            document.addEventListener('webkitfullscreenchange', () => this._updateFullscreenIcon());
        }
    },

    async loadConfig() {
        const res = await fetch(`/api/kiosk/${this.companySlug}/config`);
        if (!res.ok) throw new Error('Config not found');
        return res.json();
    },

    applyConfig(config) {
        if (config.avatar_image_url) {
            const img = document.getElementById('avatar-idle-img');
            img.src = config.avatar_image_url;
            img.style.display = 'block';
        }
        if (config.idle_timeout) this.idleTimeout = config.idle_timeout * 1000;
        this.demoMode = !!config.demo_mode_enabled;
        if (config.video_quality) this.videoQuality = config.video_quality;
    },

    async startDialog() {
        if (this.state !== 'idle') return;
        this.setState('connecting');
        UI.setSubtitle('Подключаемся...');

        try {
            const res = await fetch(`/api/kiosk/${this.companySlug}/token?language=${this.selectedLanguage}`, { method: 'POST' });
            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                if (err.detail === 'demo_limit_reached') {
                    this._showDemoLimit();
                    return;
                }
                throw new Error(err.detail || 'Ошибка сервера');
            }
            const data = await res.json();
            const { token, url, room_name } = data;

            // Demo mode: store remaining seconds and start countdown
            if (this.demoMode && data.demo_remaining_seconds != null) {
                this.demoRemainingSeconds = data.demo_remaining_seconds;
                if (this.demoRemainingSeconds <= 0) {
                    this._showDemoLimit();
                    return;
                }
            }

            UI.toggleScreen('dialog');
            await LiveKitManager.connect(url, token, {
                onDisconnect: () => this._handleDisconnect(),
                onState: (state) => this.setState(state),
                onSubtitle: (text) => UI.setSubtitle(text),
                onTranscription: (text, isFinal, participant) => {
                    const isAgent = participant?.identity?.startsWith('agent-');
                    const role = isAgent ? 'agent' : 'user';
                    UI.setTranscript(text, role, isFinal);
                    if (isAgent && isFinal) UI.setSubtitle(text);
                    if (!isAgent) UI.setUserSpeech(text, isFinal);
                    this._resetIdleTimer();
                },
                // Called once the avatar greeting is done and mic is enabled
                onReady: () => {
                    this.setState('listening');
                    UI.setSubtitle('');
                    this._resetIdleTimer();
                    this._startDemoTimer();
                },
            }, { videoQuality: this.videoQuality });
            // State stays 'connecting' until onReady fires (greeting finished)
        } catch (e) {
            console.error('Connection failed:', e);
            UI.setSubtitle(`Ошибка: ${e.message}`);
            this.setState('error');
            setTimeout(() => {
                this.setState('idle');
                UI.toggleScreen('idle');
                UI.setSubtitle('');
            }, 3000);
        }
    },

    async endDialog() {
        clearTimeout(this.reconnectTimer);
        this._clearIdleTimer();
        this._stopDemoTimer();
        await LiveKitManager.disconnect();
        UI.setSubtitle('');
        UI.stopWaveform();
        UI.setUserSpeech('', true);
        UI.hideDemoTimer();
        const log = document.getElementById('transcript-log');
        if (log) log.innerHTML = '';
        this.setState('idle');
        UI.toggleScreen('idle');
    },

    _handleDisconnect() {
        if (this.state === 'idle') return;
        this._clearIdleTimer();
        this._stopDemoTimer();
        UI.hideDemoTimer();
        UI.setSubtitle('Соединение прервано');
        this.setState('idle');
        UI.toggleScreen('idle');
        setTimeout(() => UI.setSubtitle(''), 2000);
    },

    async toggleMic() {
        const enabled = LiveKitManager.isMicEnabled();
        await LiveKitManager.setMicEnabled(!enabled);
        UI.setMicMuted(enabled);
    },

    async sendText(text) {
        if (this.state === 'idle' || this.state === 'connecting') {
            await this.startDialog();
            // Wait for connection with polling instead of fixed delay
            const start = Date.now();
            while (this.state === 'connecting' && Date.now() - start < 3000) {
                await new Promise(r => setTimeout(r, 50));
            }
        }
        await LiveKitManager.sendText(text);
        UI.setSubtitle(text);
    },

    setState(state) {
        this.state = state;
        UI.setStatus(state);
        if (state === 'listening' || state === 'speaking' || state === 'thinking') {
            this._resetIdleTimer();
        }
        if (state === 'idle') {
            this._clearIdleTimer();
        }
    },

    // --- Idle timeout (15s of silence) ---
    _resetIdleTimer() {
        clearTimeout(this.idleTimer);
        this.idleTimer = setTimeout(() => {
            if (this.state !== 'idle' && this.state !== 'connecting') {
                this.endDialog();
            }
        }, this.idleTimeout);
    },

    _clearIdleTimer() {
        clearTimeout(this.idleTimer);
        this.idleTimer = null;
    },

    // --- Fullscreen ---
    _getFullscreenElement() {
        return document.fullscreenElement || document.webkitFullscreenElement;
    },

    _toggleFullscreen() {
        const container = document.getElementById('avatar-video-container');
        if (!container) return;

        if (this._getFullscreenElement()) {
            if (document.exitFullscreen) {
                document.exitFullscreen();
            } else if (document.webkitExitFullscreen) {
                document.webkitExitFullscreen();
            }
        } else if (container.requestFullscreen) {
            container.requestFullscreen().catch(() => {});
        } else if (container.webkitRequestFullscreen) {
            container.webkitRequestFullscreen();
        } else {
            // iOS Safari: fullscreen only works on <video> elements
            const video = document.getElementById('avatar-video');
            if (video && video.webkitEnterFullscreen) {
                video.webkitEnterFullscreen();
            }
        }
    },

    _updateFullscreenIcon() {
        const btn = document.getElementById('btn-fullscreen');
        if (!btn) return;
        const isFs = !!this._getFullscreenElement();
        btn.setAttribute('aria-label', isFs ? 'Выйти из полноэкранного режима' : 'На весь экран');
        btn.innerHTML = isFs
            ? '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="20" height="20"><path d="M5 16h3v3h2v-5H5v2zm3-8H5v2h5V5H8v3zm6 11h2v-3h3v-2h-5v5zm2-11V5h-2v5h5V8h-3z"/></svg>'
            : '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="20" height="20"><path d="M7 14H5v5h5v-2H7v-3zm-2-4h2V7h3V5H5v5zm12 7h-3v2h5v-5h-2v3zM14 5v2h3v3h2V5h-5z"/></svg>';
    },

    // --- Demo mode ---
    _startDemoTimer() {
        if (!this.demoMode || this.demoRemainingSeconds == null) return;
        this.demoStartTime = Date.now();
        UI.showDemoTimer(Math.ceil(this.demoRemainingSeconds));
        this.demoTimer = setInterval(() => {
            const elapsed = (Date.now() - this.demoStartTime) / 1000;
            const remaining = Math.max(0, this.demoRemainingSeconds - elapsed);
            UI.showDemoTimer(Math.ceil(remaining));
            if (remaining <= 0) {
                this._stopDemoTimer();
                this._reportDemoUsage(elapsed);
                this.endDialog();
                this._showDemoLimit();
            }
        }, 1000);
    },

    _stopDemoTimer() {
        if (this.demoTimer) {
            clearInterval(this.demoTimer);
            this.demoTimer = null;
        }
        if (this.demoMode && this.demoStartTime) {
            const elapsed = (Date.now() - this.demoStartTime) / 1000;
            this._reportDemoUsage(elapsed);
            this.demoStartTime = null;
        }
    },

    _reportDemoUsage(seconds) {
        if (!seconds || seconds <= 0) return;
        fetch(`/api/kiosk/${this.companySlug}/demo-usage`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ seconds_used: seconds }),
        }).catch(() => {});
    },

    _showDemoLimit() {
        this.setState('idle');
        UI.toggleScreen('demo-limit');
    },
};

document.addEventListener('DOMContentLoaded', () => AIGITO.init());
