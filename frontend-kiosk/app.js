'use strict';

const AIGITO = {
    companySlug: null,
    state: 'idle', // idle | connecting | listening | thinking | speaking

    async init() {
        // Extract company slug from URL: /kiosk/dental-smile
        const parts = window.location.pathname.split('/');
        this.companySlug = parts[parts.length - 1] || parts[parts.length - 2] || 'demo';

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
        this.setState('connecting');

        try {
            const res = await fetch(`/api/kiosk/${this.companySlug}/token`, { method: 'POST' });
            if (!res.ok) throw new Error('Failed to get LiveKit token');
            const { token, url } = await res.json();

            UI.toggleScreen('dialog');
            await LiveKitManager.connect(url, token);
            this.setState('listening');
        } catch (e) {
            console.error('Connection failed:', e);
            UI.setSubtitle('Ошибка подключения. Попробуйте ещё раз.');
            this.setState('idle');
            UI.toggleScreen('idle');
        }
    },

    async endDialog() {
        await LiveKitManager.disconnect();
        UI.setSubtitle('');
        UI.stopWaveform();
        this.setState('idle');
        UI.toggleScreen('idle');
    },

    async toggleMic() {
        const enabled = LiveKitManager.room?.localParticipant?.isMicrophoneEnabled ?? true;
        await LiveKitManager.setMicEnabled(!enabled);
        UI.setMicMuted(enabled); // enabled → now muted
    },

    async sendText(text) {
        await LiveKitManager.sendText(text);
        UI.setSubtitle(text);
    },

    setState(state) {
        this.state = state;
        UI.setStatus(state);
    },
};

document.addEventListener('DOMContentLoaded', () => AIGITO.init());
