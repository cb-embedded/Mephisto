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
        
        for (let i = 0; i < length; i += 3) {
            const addr = startAddr + i;
            if (addr + 2 >= this.binaryData.length) break;

            const noteId = this.binaryData[addr];
            const duration = this.binaryData[addr + 1];
            const command = this.binaryData[addr + 2];

            // Stop if we hit end marker or invalid data
            if (noteId === 0xFF || (noteId === 0 && duration === 0 && command === 0)) {
                break;
            }

            // Skip if it looks like non-music data
            if (duration === 0 || duration > 0x80) continue;

            notes.push({
                noteId: noteId,
                duration: duration,
                command: command,
                frequency: this.noteIdToFrequency(noteId),
                durationMs: duration * 50 // Convert to milliseconds (approximate)
            });

            // Stop at reasonable length
            if (notes.length > 100) break;
        }

        return notes;
    }

    noteIdToFrequency(noteId) {
        // Map note IDs to frequencies
        // Based on analysis: 0x31-0x4C are note values
        const noteMap = {
            // Octave markers
            0x31: 130.81, 0x32: 138.59, 0x33: 146.83, 0x34: 155.56,
            0x35: 164.81, 0x36: 174.61, 0x37: 185.00, 0x38: 196.00,
            0x39: 207.65, 0x3A: 220.00, 0x3B: 233.08, 0x3C: 246.94,
            
            // Note letters (approximate middle octave)
            0x41: 220.00, // A
            0x42: 246.94, // B
            0x43: 261.63, // C
            0x44: 293.66, // D
            0x45: 329.63, // E
            0x46: 349.23, // F
            0x47: 392.00, // G
            0x48: 440.00, // H (A)
            0x49: 493.88, // I (B)
            0x4A: 523.25, // J (C)
            0x4B: 587.33, // K (D)
            0x4C: 659.25, // L (E)
            
            0x00: 0 // Rest
        };

        return noteMap[noteId] || 440; // Default to A440
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

            if (note.frequency > 0) {
                // Play note with moderate amplitude
                this.synth.playNote(channel, note.frequency, 12, note.durationMs);
            }

            // Wait for note duration
            await this.sleep(note.durationMs);
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
