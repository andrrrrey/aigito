'use strict';

const LiveKitManager = {
    room: null,
    _callbacks: {},
    videoQuality: 'auto',
    _greetingDone: false,        // mic stays off until agent finishes greeting
    _agentWasSpeaking: false,    // tracks that agent spoke at least once (greeting)
    _greetingTimer: null,        // safety timeout to enable mic if nothing fires
    _silenceTimer: null,         // debounce for ActiveSpeakersChanged silence detection
    _audioContext: null,          // AudioContext for unlocking autoplay

    async connect(url, token, callbacks = {}, options = {}) {
        this._callbacks = callbacks;
        this.videoQuality = options.videoQuality || 'auto';
        this._greetingDone = false;
        this._agentWasSpeaking = false;
        clearTimeout(this._greetingTimer);
        clearTimeout(this._silenceTimer);

        const isMax = this.videoQuality === 'max';

        this.room = new LivekitClient.Room({
            adaptiveStream: true,
            dynacast: true,
            videoCaptureDefaults: {
                resolution: isMax
                    ? LivekitClient.VideoPresets.h720.resolution
                    : LivekitClient.VideoPresets.h360.resolution,
            },
        });

        this.room.on(LivekitClient.RoomEvent.TrackSubscribed, (track, publication, participant) => {
            if (track.kind === LivekitClient.Track.Kind.Video) {
                if (isMax) {
                    // Force highest quality — ignore adaptive stream
                    if (publication.setVideoQuality) {
                        publication.setVideoQuality(LivekitClient.VideoQuality.HIGH);
                    }
                    if (publication.setVideoDimensions) {
                        publication.setVideoDimensions({ width: 1024, height: 1024 });
                    }
                }
                // "auto": don't call setVideoQuality/setVideoDimensions —
                // let adaptiveStream adjust quality based on connection
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
                audioEl.src = '';
                audioEl.srcObject = null;
                track.attach(audioEl);
                const p = audioEl.play(); if (p) p.catch(() => {});
            }
        });

        this.room.on(LivekitClient.RoomEvent.TrackUnsubscribed, (track) => {
            track.detach();
        });

        // PRIMARY: LiveKit audio-level based speaking detection.
        // When agent stops speaking after the greeting, enable mic.
        this.room.on(LivekitClient.RoomEvent.ActiveSpeakersChanged, (speakers) => {
            if (this._greetingDone) return;
            // Any non-local speaking participant = agent
            const agentSpeaking = speakers.some(p => !p.isLocal);
            if (agentSpeaking) {
                this._agentWasSpeaking = true;
                clearTimeout(this._silenceTimer);
                this._silenceTimer = null;
                UI.startWaveform();
            } else if (this._agentWasSpeaking && !this._silenceTimer) {
                // Agent went silent — debounce 600ms to avoid mid-sentence gaps
                this._silenceTimer = setTimeout(() => {
                    this._silenceTimer = null;
                    if (!this._greetingDone) this._enableMicAfterGreeting();
                }, 600);
            }
        });

        this.room.on(LivekitClient.RoomEvent.DataReceived, (payload) => {
            try {
                const data = JSON.parse(new TextDecoder().decode(payload));
                if (data.type === 'transcript' && this._callbacks.onSubtitle) {
                    this._callbacks.onSubtitle(data.content);
                }
                if (data.type === 'state') {
                    if (!this._greetingDone) {
                        // Secondary: data channel state events (livekit-agents may or may not send these)
                        if (data.state === 'speaking') {
                            this._agentWasSpeaking = true;
                            UI.startWaveform();
                        } else if (data.state === 'listening' && this._agentWasSpeaking) {
                            this._enableMicAfterGreeting();
                        }
                    } else {
                        if (this._callbacks.onState) this._callbacks.onState(data.state);
                        if (data.state === 'speaking') UI.startWaveform();
                        else UI.stopWaveform();
                    }
                }
            } catch (e) { /* ignore malformed data */ }
        });

        this.room.on(LivekitClient.RoomEvent.ParticipantConnected, (participant) => {
            // Agent connected — don't set listening yet; wait for greeting to finish
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
                // Tertiary: any final transcription while mic is off = must be agent greeting done
                if (!this._greetingDone && isFinal) {
                    this._enableMicAfterGreeting();
                }
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
        // Mic is NOT enabled here — it will be enabled after the greeting finishes.
        // Hard fallback: if no audio activity detected within 15s, enable mic anyway.
        this._greetingTimer = setTimeout(() => {
            if (!this._greetingDone) this._enableMicAfterGreeting();
        }, 15000);
    },

    _enableMicAfterGreeting() {
        clearTimeout(this._greetingTimer);
        clearTimeout(this._silenceTimer);
        this._greetingDone = true;
        UI.stopWaveform();
        if (this.room) {
            this.room.localParticipant.setMicrophoneEnabled(true);
        }
        if (this._callbacks.onReady) this._callbacks.onReady();
    },

    async disconnect() {
        clearTimeout(this._greetingTimer);
        clearTimeout(this._silenceTimer);
        this._greetingDone = false;
        this._agentWasSpeaking = false;
        this._silenceTimer = null;
        if (this.room) {
            await this.room.disconnect();
            this.room = null;
        }
        // Remove audio element
        const audioEl = document.getElementById('avatar-audio');
        if (audioEl) audioEl.remove();
        // Close AudioContext to free resources
        if (this._audioContext) {
            this._audioContext.close().catch(() => {});
            this._audioContext = null;
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

    isMicEnabled() {
        return this.room?.localParticipant?.isMicrophoneEnabled ?? true;
    },
};
