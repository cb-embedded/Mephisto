# GitHub Pages - Melody Player

This directory contains a web-based melody player for testing the music data extracted from the 8051 sound CPU firmware.

## Files

- `index.html` - Main player interface
- `melody-player.js` - JavaScript implementation of melody playback using Web Audio API
- `sound_cpu_8051.bin` - Original 8051 firmware (required for playback)

## How It Works

The player:
1. Loads the `sound_cpu_8051.bin` file
2. Extracts melody data from addresses 0x2D00-0x3200
3. Parses the music format: `[Note_ID] [Duration] [Command]`
4. Synthesizes audio using Web Audio API (square waves like AY-3-8910)
5. Provides buttons to play each discovered melody

## Accessing the Player

Once GitHub Pages is enabled for this repository, access the player at:
`https://cb-embedded.github.io/Mephisto/`

## Music Format

- **Note IDs**: 0x31-0x4C (ASCII-like: A, D, F, G, etc.)
- **Duration**: In ticks (converted to milliseconds)
- **Command**: 0x68, 0x69, 0x70, etc. (indicates channel/variant)

## Technical Details

- Uses Web Audio API OscillatorNode with square wave
- Three channels (A, B, C) simulating AY-3-8910
- Real-time channel status display
- Play/stop controls for each melody
