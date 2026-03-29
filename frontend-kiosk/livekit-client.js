'use strict';

const LiveKitManager = {
    room: null,

    async connect(url, token) {
        this.room = new LivekitClient.Room({
            adaptiveStream: true,
            dynacast: true,
        });

        this.room.on(LivekitClient.RoomEvent.TrackSubscribed, (track, publication, participant) => {
            if (track.kind === LivekitClient.Track.Kind.Video) {
                const videoEl = document.getElementById('avatar-video');
                if (videoEl) track.attach(videoEl);
            }
            if (track.kind === LivekitClient.Track.Kind.Audio) {
                const audioEl = new Audio();
                audioEl.autoplay = true;
                track.attach(audioEl);
                document.body.appendChild(audioEl);
            }
        });

        this.room.on(LivekitClient.RoomEvent.TrackUnsubscribed, (track) => {
            track.detach();
        });

        this.room.on(LivekitClient.RoomEvent.DataReceived, (payload, participant) => {
            try {
                const data = JSON.parse(new TextDecoder().decode(payload));
                if (data.type === 'transcript') {
                    UI.setSubtitle(data.content);
                } else if (data.type === 'state') {
                    UI.setStatus(data.state);
                    if (data.state === 'speaking') UI.startWaveform();
                    else UI.stopWaveform();
                }
            } catch (e) { /* ignore */ }
        });

        this.room.on(LivekitClient.RoomEvent.Disconnected, () => {
            UI.toggleScreen('idle');
            UI.setStatus('idle');
        });

        await this.room.connect(url, token);
        await this.room.localParticipant.setMicrophoneEnabled(true);
    },

    async disconnect() {
        if (this.room) {
            await this.room.disconnect();
            this.room = null;
        }
    },

    async sendText(text) {
        if (!this.room) return;
        const data = new TextEncoder().encode(JSON.stringify({ type: 'text', content: text }));
        await this.room.localParticipant.publishData(data, { reliable: true });
    },

    async setMicEnabled(enabled) {
        if (this.room) {
            await this.room.localParticipant.setMicrophoneEnabled(enabled);
        }
    },
};
