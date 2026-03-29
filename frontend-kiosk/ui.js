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

    toggleScreen(screen) {
        // screen: 'idle' | 'dialog'
        document.getElementById('screen-idle').classList.toggle('active', screen === 'idle');
        document.getElementById('screen-dialog').classList.toggle('active', screen === 'dialog');
    },

    setMicMuted(muted) {
        const btn = document.getElementById('btn-mic');
        if (btn) btn.classList.toggle('muted', muted);
    },

    startWaveform() {
        document.querySelectorAll('#waveform-left, #waveform-right').forEach(wf => {
            wf.innerHTML = '';
            for (let i = 0; i < 5; i++) {
                const bar = document.createElement('div');
                bar.className = 'waveform-bar active';
                bar.style.animationDelay = `${i * 0.1}s`;
                bar.style.height = `${20 + Math.random() * 20}px`;
                wf.appendChild(bar);
            }
        });
    },

    stopWaveform() {
        document.querySelectorAll('.waveform-bar').forEach(bar => bar.classList.remove('active'));
    },

    updateChips(chips) {
        const container = document.getElementById('chips-container');
        if (!container || !chips) return;
        container.innerHTML = chips
            .map(text => `<button class="chip" data-text="${text}">${text}</button>`)
            .join('');
        container.querySelectorAll('.chip').forEach(chip => {
            chip.addEventListener('click', () => window.AIGITO && AIGITO.sendText(chip.dataset.text));
        });
    },
};
