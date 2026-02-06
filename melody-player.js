// 8051 Sound CPU - Melody Player
// Plays melodies extracted from sound_cpu_8051.bin using Web Audio API

class AY3810Synth {
    constructor() {
        this.audioContext = null;
        this.channels = [null, null, null];
        this.masterGain = null;
    }

    async init() {
        this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        this.masterGain = this.audioContext.createGain();
        this.masterGain.gain.value = 0.3;
        this.masterGain.connect(this.audioContext.destination);
    }

    playNote(channel, frequency, amplitude, duration) {
        if (!this.audioContext) return;

        // Stop any existing note on this channel
        this.stopChannel(channel);

        // Create oscillator and gain
        const oscillator = this.audioContext.createOscillator();
        const gainNode = this.audioContext.createGain();

        oscillator.type = 'square'; // AY-3-8910 uses square waves
        oscillator.frequency.value = frequency;

        // Set amplitude (0-15 scale to 0-1)
        const volume = amplitude / 15 * 0.3;
        gainNode.gain.value = volume;

        oscillator.connect(gainNode);
        gainNode.connect(this.masterGain);

        oscillator.start();
        
        // Store reference
        this.channels[channel] = {
            oscillator: oscillator,
            gainNode: gainNode,
            frequency: frequency,
            amplitude: amplitude
        };

        // Auto-stop after duration if specified
        if (duration) {
            setTimeout(() => this.stopChannel(channel), duration);
        }
    }

    stopChannel(channel) {
        if (this.channels[channel]) {
            try {
                this.channels[channel].oscillator.stop();
            } catch (e) {
                // Already stopped
            }
            this.channels[channel] = null;
        }
    }

    stopAll() {
        for (let i = 0; i < 3; i++) {
            this.stopChannel(i);
        }
    }

    getChannelInfo(channel) {
        if (this.channels[channel]) {
            return {
                active: true,
                frequency: this.channels[channel].frequency,
                amplitude: this.channels[channel].amplitude
            };
        }
        return { active: false };
    }
}

class MelodyPlayer {
    constructor() {
        this.synth = new AY3810Synth();
        this.melodies = [];
        this.currentMelody = null;
        this.playing = false;
        this.binaryData = null;
        this.speedMultiplier = 1.0;
        
        // Constants for melody parsing
        this.MAX_NOTES = 100;
        this.MAX_DURATION = 0x80; // Valid duration range: 0x01-0x7F (0x00 and values >= 0x80 are invalid)
        this.DURATION_TO_MS_FACTOR = 50; // Convert duration units to milliseconds
        this.CHANNEL_CMDS = new Set([0x68, 0x69, 0x70, 0x71, 0x72]); // Channel/command marker bytes
    }

    async init() {
        await this.synth.init();
        await this.loadBinary();
        this.extractMelodies();
        this.setupUI();
    }

    async loadBinary() {
        try {
            const response = await fetch('sound_cpu_8051.bin');
            const arrayBuffer = await response.arrayBuffer();
            this.binaryData = new Uint8Array(arrayBuffer);
            this.updateStatus('Binary loaded successfully (' + this.binaryData.length + ' bytes)');
        } catch (error) {
            this.updateStatus('Error loading binary: ' + error.message);
        }
    }

    extractMelodies() {
        if (!this.binaryData) return;

        // Music data is at 0x2D00-0x3200
        // Format: [Note_ID] [Duration] [Command]
        
        // Define melody start addresses based on analysis
        const melodyAddresses = [
            { addr: 0x2D00, name: 'Melody 1', length: 0x80 },
            { addr: 0x2D80, name: 'Melody 2', length: 0x80 },
            { addr: 0x2DD0, name: 'Melody 3 (Sequence)', length: 0x60 },
            { addr: 0x2E00, name: 'Melody 4', length: 0x80 },
            { addr: 0x2E80, name: 'Melody 5', length: 0x80 },
            { addr: 0x2F00, name: 'Melody 6', length: 0x80 },
            { addr: 0x2F80, name: 'Melody 7', length: 0x80 },
            { addr: 0x3000, name: 'Melody 8', length: 0x80 },
            { addr: 0x3080, name: 'Melody 9', length: 0x80 },
            { addr: 0x3100, name: 'Melody 10', length: 0x80 },
        ];

        for (const melodyDef of melodyAddresses) {
            const notes = this.parseMelody(melodyDef.addr, melodyDef.length);
            if (notes.length > 0) {
                this.melodies.push({
                    name: melodyDef.name,
                    address: melodyDef.addr,
                    notes: notes
                });
            }
        }

        this.updateStatus(`Found ${this.melodies.length} melodies in binary`);
    }

    parseMelody(startAddr, length) {
        const notes = [];
        
        let i = 0;
        while (i < length && notes.length < this.MAX_NOTES) {
            const addr = startAddr + i;
            if (addr + 2 >= this.binaryData.length) break;

            const b1 = this.binaryData[addr];
            const b2 = this.binaryData[addr + 1];
            const b3 = this.binaryData[addr + 2];

            let noteId, duration, command;

            // Smart format detection: Check if b1 or b3 is a channel command
            if (this.CHANNEL_CMDS.has(b1)) {
                // Format: [Command][Note][Duration]
                command = b1;
                noteId = b2;
                duration = b3;
                i += 3;
            } else if (this.CHANNEL_CMDS.has(b3)) {
                // Format: [Note][Duration][Command]
                noteId = b1;
                duration = b2;
                command = b3;
                i += 3;
            } else {
                // Stop if we hit end markers or padding
                if (b1 === 0xFF || (b1 === 0 && b2 === 0)) {
                    break;
                }
                // Skip byte and try next position (misalignment or header)
                i += 1;
                continue;
            }

            // Validate and add note
            if (duration > 0 && duration < this.MAX_DURATION) {
                notes.push({
                    noteId: noteId,
                    duration: duration,
                    command: command,
                    frequency: this.noteIdToFrequency(noteId),
                    durationMs: duration * this.DURATION_TO_MS_FACTOR
                });
            }
        }

        return notes;
    }

    noteIdToFrequency(noteId) {
        // Map note IDs to frequencies
        // The firmware uses note IDs in two ranges:
        // - 0x31-0x3C: Lower octave (12 chromatic notes from C3 to B3)
        // - 0x41-0x51: Higher octave (17 chromatic notes from C4 to E5)
        // Note: The hex values don't directly correspond to musical note names
        //       (e.g., 0x41 maps to C4, not A)
        
        const noteMap = {
            // Lower octave (0x31-0x3C)
            0x31: 130.81, // C3
            0x32: 138.59, // C#3
            0x33: 146.83, // D3
            0x34: 155.56, // D#3
            0x35: 164.81, // E3
            0x36: 174.61, // F3
            0x37: 185.00, // F#3
            0x38: 196.00, // G3
            0x39: 207.65, // G#3
            0x3A: 220.00, // A3
            0x3B: 233.08, // A#3
            0x3C: 246.94, // B3
            
            // Middle octave (0x41-0x51) - ASCII 'A'-'Q'
            0x41: 261.63, // C4 (Middle C)
            0x42: 277.18, // C#4
            0x43: 293.66, // D4
            0x44: 311.13, // D#4
            0x45: 329.63, // E4
            0x46: 349.23, // F4
            0x47: 369.99, // F#4
            0x48: 392.00, // G4
            0x49: 415.30, // G#4
            0x4A: 440.00, // A4 (Concert pitch)
            0x4B: 466.16, // A#4
            0x4C: 493.88, // B4
            0x4D: 523.25, // C5
            0x4E: 554.37, // C#5
            0x4F: 587.33, // D5
            0x50: 622.25, // D#5
            0x51: 659.25, // E5
            
            0x00: 0 // Rest/silence
        };

        return noteMap[noteId] || 440; // Default to A4 if unknown
    }

    setupUI() {
        const grid = document.getElementById('melodyGrid');
        grid.innerHTML = '';

        this.melodies.forEach((melody, index) => {
            const button = document.createElement('button');
            button.className = 'melody-button';
            button.textContent = `${melody.name} (${melody.notes.length} notes)`;
            button.onclick = () => this.playMelody(index, button);
            grid.appendChild(button);
        });

        // Setup control buttons
        document.getElementById('stopButton').onclick = () => this.stop();
        document.getElementById('testNoteButton').onclick = () => this.testNote();

        // Setup speed slider
        const speedSlider = document.getElementById('speedSlider');
        const speedValue = document.getElementById('speedValue');
        if (speedSlider && speedValue) {
            speedSlider.addEventListener('input', (e) => {
                this.speedMultiplier = parseFloat(e.target.value);
                speedValue.textContent = `${this.speedMultiplier.toFixed(1)}x`;
            });
        }

        // Update channel info periodically
        setInterval(() => this.updateChannelDisplay(), 100);
    }

    async playMelody(index, button) {
        if (this.playing) {
            this.stop();
        }

        const melody = this.melodies[index];
        this.currentMelody = melody;
        this.playing = true;

        // Update button state
        document.querySelectorAll('.melody-button').forEach(btn => btn.classList.remove('playing'));
        button.classList.add('playing');

        this.updateStatus(`Playing: ${melody.name} @ 0x${melody.address.toString(16).toUpperCase()}`);

        // Play notes sequentially
        for (let i = 0; i < melody.notes.length && this.playing; i++) {
            const note = melody.notes[i];
            
            // Determine channel based on command byte
            let channel = 0;
            if (note.command === 0x69 || note.command === 0x71) channel = 1;
            else if (note.command === 0x70 || note.command === 0x72) channel = 2;

            // Calculate adjusted duration based on speed multiplier
            const adjustedDuration = note.durationMs / this.speedMultiplier;

            if (note.frequency > 0) {
                // Play note with moderate amplitude
                this.synth.playNote(channel, note.frequency, 12, adjustedDuration);
            }

            // Wait for note duration
            await this.sleep(adjustedDuration);
        }

        this.playing = false;
        button.classList.remove('playing');
        this.updateStatus(`Finished playing: ${melody.name}`);
    }

    stop() {
        this.playing = false;
        this.synth.stopAll();
        document.querySelectorAll('.melody-button').forEach(btn => btn.classList.remove('playing'));
        this.updateStatus('Stopped');
    }

    testNote() {
        this.updateStatus('Testing A440 for 1 second...');
        this.synth.playNote(0, 440, 15, 1000);
    }

    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    updateStatus(message) {
        document.getElementById('statusDisplay').textContent = message;
    }

    updateChannelDisplay() {
        const channelInfo = document.getElementById('channelInfo');
        const channels = ['A', 'B', 'C'];
        
        channelInfo.innerHTML = channels.map((name, i) => {
            const info = this.synth.getChannelInfo(i);
            let content = 'Idle';
            
            if (info.active) {
                content = `Freq: ${info.frequency.toFixed(2)} Hz<br>Amp: ${info.amplitude}/15`;
            }
            
            return `
                <div class="channel">
                    <h3>Channel ${name}</h3>
                    <div class="channel-data">${content}</div>
                </div>
            `;
        }).join('');
    }
}

// Initialize player when page loads
let player;

window.addEventListener('load', async () => {
    player = new MelodyPlayer();
    await player.init();
});
