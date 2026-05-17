'use strict';

const UI = {
    setStatus(state) {
        const indicator = document.getElementById('status-indicator');
        if (indicator) {
            indicator.className = `status-${state}`;
        }
    },

    setSubtitle(text) {
        const el = document.getElementById('subtitles');
        if (el) el.textContent = text;
    },

    setUserSpeech(text, isFinal) {
        const el = document.getElementById('user-speech-box');
        if (!el) return;
        el.textContent = text;
        if (isFinal && text) {
            setTimeout(() => { if (el.textContent === text) el.textContent = ''; }, 3000);
        }
    },

    setTranscript(text, role, isFinal) {
        const el = document.getElementById('transcript-log');
        if (!el) return;
        // Update last line if not final, otherwise add new line
        const prefix = role === 'agent' ? 'Ассистент' : 'Вы';
        const cls = role === 'agent' ? 'transcript-agent' : 'transcript-user';
        let lastEntry = el.querySelector('.transcript-entry:last-child');
        if (lastEntry && lastEntry.dataset.role === role && !lastEntry.dataset.final) {
            lastEntry.querySelector('.transcript-text').textContent = text;
            if (isFinal) lastEntry.dataset.final = 'true';
        } else {
            const entry = document.createElement('div');
            entry.className = `transcript-entry ${cls}`;
            entry.dataset.role = role;
            if (isFinal) entry.dataset.final = 'true';
            entry.innerHTML = `<span class="transcript-role">${prefix}:</span> <span class="transcript-text">${text}</span>`;
            el.appendChild(entry);
        }
        el.scrollTop = el.scrollHeight;
    },

    toggleScreen(screen) {
        // screen: 'idle' | 'dialog' | 'demo-limit'
        document.getElementById('screen-idle').classList.toggle('active', screen === 'idle');
        document.getElementById('screen-dialog').classList.toggle('active', screen === 'dialog');
        const demoLimitEl = document.getElementById('screen-demo-limit');
        if (demoLimitEl) demoLimitEl.classList.toggle('active', screen === 'demo-limit');
    },

    setMicMuted(muted) {
        const btn = document.getElementById('btn-mic');
        if (btn) btn.classList.toggle('muted', muted);
    },

    _waveformEls: null,

    _getWaveformEls() {
        if (!this._waveformEls)
            this._waveformEls = ['waveform-left', 'waveform-right'].map(id => document.getElementById(id));
        return this._waveformEls;
    },

    startWaveform() {
        this._getWaveformEls().forEach(wf => wf?.classList.add('active'));
    },

    stopWaveform() {
        this._getWaveformEls().forEach(wf => wf?.classList.remove('active'));
    },

    showDemoTimer(seconds) {
        const el = document.getElementById('demo-timer');
        if (!el) return;
        const m = Math.floor(seconds / 60);
        const s = seconds % 60;
        el.textContent = `${m}:${String(s).padStart(2, '0')}`;
        el.style.display = 'block';
        el.classList.toggle('demo-timer-warning', seconds <= 10);
    },

    hideDemoTimer() {
        const el = document.getElementById('demo-timer');
        if (el) el.style.display = 'none';
    },

    updateChips(chips) {
        const container = document.getElementById('chips-container');
        if (!container || !chips) return;
        container.innerHTML = chips
            .map(text => `<button class="chip" data-text="${text}">${text}</button>`)
            .join('');
        container.onclick = (e) => {
            const chip = e.target.closest('.chip');
            if (chip && window.AIGITO) AIGITO.sendText(chip.dataset.text);
        };
    },
};
