'use strict';

const AIGITO = {
    companySlug: null,
    state: 'idle', // idle | connecting | listening | thinking | speaking | error
    reconnectTimer: null,

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

        document.querySelectorAll('.chip').forEach(chip => {
            chip.addEventListener('click', () => this.sendText(chip.dataset.text));
        });
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
        if (config.chips && config.chips.length) {
            UI.updateChips(config.chips);
        }
    },

    async startDialog() {
        if (this.state !== 'idle') return;
        this.setState('connecting');
        UI.setSubtitle('Подключаемся...');

        try {
            const res = await fetch(`/api/kiosk/${this.companySlug}/token`, { method: 'POST' });
            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                throw new Error(err.detail || 'Ошибка сервера');
            }
            const { token, url, room_name } = await res.json();

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
                },
            });
            this.setState('listening');
            UI.setSubtitle('');
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
        await LiveKitManager.disconnect();
        UI.setSubtitle('');
        UI.stopWaveform();
        const log = document.getElementById('transcript-log');
        if (log) log.innerHTML = '';
        this.setState('idle');
        UI.toggleScreen('idle');
    },

    _handleDisconnect() {
        if (this.state === 'idle') return;
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
            // Wait briefly for connection
            await new Promise(r => setTimeout(r, 1500));
        }
        await LiveKitManager.sendText(text);
        UI.setSubtitle(text);
    },

    setState(state) {
        this.state = state;
        UI.setStatus(state);
    },
};

document.addEventListener('DOMContentLoaded', () => AIGITO.init());
