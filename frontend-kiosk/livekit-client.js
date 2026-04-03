'use strict';

const LiveKitManager = {
    room: null,
    _callbacks: {},

    async connect(url, token, callbacks = {}) {
        this._callbacks = callbacks;

        this.room = new LivekitClient.Room({
            adaptiveStream: true,
            dynacast: true,
            // Optimize video: prefer lower quality for faster delivery
            videoCaptureDefaults: {
                resolution: LivekitClient.VideoPresets.h360.resolution,
            },
        });

        this.room.on(LivekitClient.RoomEvent.TrackSubscribed, (track, publication, participant) => {
            if (track.kind === LivekitClient.Track.Kind.Video) {
                // Request lower quality video to reduce latency
                if (publication.setVideoQuality) {
                    publication.setVideoQuality(LivekitClient.VideoQuality.MEDIUM);
                }
                if (publication.setVideoDimensions) {
                    publication.setVideoDimensions({ width: 512, height: 512 });
                }
                const videoEl = document.getElementById('avatar-video');
                if (videoEl) track.attach(videoEl);
            }
            if (track.kind === LivekitClient.Track.Kind.Audio) {
                let audioEl = document.getElementById('avatar-audio');
                if (!audioEl) {
                    audioEl = document.createElement('audio');
                    audioEl.id = 'avatar-audio';
                    audioEl.autoplay = true;
                    document.body.appendChild(audioEl);
                }
                track.attach(audioEl);
            }
        });

        this.room.on(LivekitClient.RoomEvent.TrackUnsubscribed, (track) => {
            track.detach();
        });

        this.room.on(LivekitClient.RoomEvent.DataReceived, (payload) => {
            try {
                const data = JSON.parse(new TextDecoder().decode(payload));
                if (data.type === 'transcript' && this._callbacks.onSubtitle) {
                    this._callbacks.onSubtitle(data.content);
                }
                if (data.type === 'state' && this._callbacks.onState) {
                    this._callbacks.onState(data.state);
                    if (data.state === 'speaking') UI.startWaveform();
                    else UI.stopWaveform();
                }
            } catch (e) { /* ignore malformed data */ }
        });

        this.room.on(LivekitClient.RoomEvent.ParticipantConnected, (participant) => {
            // Agent connected — signal to show listening state
            if (this._callbacks.onState) this._callbacks.onState('listening');
        });

        this.room.on(LivekitClient.RoomEvent.Disconnected, () => {
            if (this._callbacks.onDisconnect) this._callbacks.onDisconnect();
        });

        // Connection quality monitoring — log degradation for diagnostics
        this.room.on(LivekitClient.RoomEvent.ConnectionQualityChanged, (quality, participant) => {
            if (participant && !participant.isLocal) {
                const indicator = document.getElementById('status-indicator');
                if (indicator && quality === LivekitClient.ConnectionQuality.Poor) {
                    indicator.title = 'Плохое соединение';
                }
            }
        });

        // Handle reconnection — show user that connection is recovering
        this.room.on(LivekitClient.RoomEvent.Reconnecting, () => {
            if (this._callbacks.onState) this._callbacks.onState('connecting');
        });
        this.room.on(LivekitClient.RoomEvent.Reconnected, () => {
            if (this._callbacks.onState) this._callbacks.onState('listening');
        });

        // Transcription events from livekit-agents
        this.room.on(LivekitClient.RoomEvent.TranscriptionReceived, (segments, participant) => {
            if (segments && segments.length > 0) {
                const text = segments.map(s => s.text).join(' ');
                const isFinal = segments.some(s => s.final);
                if (this._callbacks.onTranscription) {
                    this._callbacks.onTranscription(text, isFinal, participant);
                }
            }
        });

        await this.room.connect(url, token, {
            autoSubscribe: true,
            // Faster reconnection on network issues
            reconnectPolicy: {
                maxRetries: 5,
                initialDelay: 300,
                maxDelay: 5000,
            },
        });
        await this.room.localParticipant.setMicrophoneEnabled(true);
    },

    async disconnect() {
        if (this.room) {
            await this.room.disconnect();
            this.room = null;
        }
        // Remove audio element
        const audioEl = document.getElementById('avatar-audio');
        if (audioEl) audioEl.remove();
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

    isMicEnabled() {
        return this.room?.localParticipant?.isMicrophoneEnabled ?? true;
    },
};
