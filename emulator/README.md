# 8051 + AY-3-8910 Real-Time Music Emulator

This directory contains a complete emulator system that connects an 8051 CPU emulator to an AY-3-8910 sound chip emulator, with UART input via stdin and real-time audio output.

## Features

- **Complete 8051 CPU Emulation**: Executes the actual `sound_cpu_8051.bin` firmware
- **AY-3-8910 Sound Chip**: Full emulation of the 3-channel programmable sound generator
- **Real-Time Audio**: Generates actual audio output you can hear
- **UART Input**: Send commands via stdin in hex format
- **Interactive**: Type commands and hear music in real-time

## Requirements

```bash
pip install numpy pyaudio
```

**Note**: On some systems, you may need to install PortAudio first:
- Ubuntu/Debian: `sudo apt-get install portaudio19-dev`
- macOS: `brew install portaudio`
- Windows: PyAudio includes PortAudio

## Usage

### Basic Usage

```bash
cd emulator
python3 main.py
```

The emulator will start and wait for UART input via stdin.

### Sending Commands

Commands use the protocol format: `[START] [CMD] [DATA...] [END]`

**Example: Play Middle C on Channel A**
```
B5 A4 00 DD 01 0F B0
```

**Example: Play A440 on Channel B**
```
B5 A4 01 1C 01 0C B0
```

**Example: Play a Chord (C-E-G)**
```
B5 A4 00 DD 01 0A B0
B5 A4 01 7A 01 0A B0
B5 A4 02 3E 01 0A B0
```

**Example: Stop all channels**
```
B5 A6 B0
```

### Interactive Commands

While the emulator is running, you can type:

- `s` or `status` - Show current AY-3-8910 state
- `q` or `quit` - Exit the emulator
- Hex bytes - Send UART command (e.g., `B5 A4 00 DD 01 0F B0`)

## Command Protocol

### Start Markers
- `0xB5` or `0xB6` - Required at the beginning of every command

### Commands
- `0xA0` - Status/control
- `0xA2` - Set frequency low byte: `[channel] [value]`
- `0xA3` - Set frequency high byte: `[channel] [value]`
- `0xA4` - Play note: `[channel] [freq_lo] [freq_hi] [amplitude]`
- `0xA6` - Stop all channels
- `0xA7` - Special command 1
- `0xA8` - Special command 2

### End Marker
- `0xB0` - Required at the end of every command

### Data Format for Note Command (0xA4)

```
B5 A4 [CH] [FL] [FH] [AMP] B0

CH  = Channel (0=A, 1=B, 2=C)
FL  = Frequency low byte
FH  = Frequency high byte (only lower 4 bits used)
AMP = Amplitude (0x00-0x0F)
```

## Frequency Calculation

The AY-3-8910 uses period values, not direct frequencies:

```
Period = Clock_Frequency / (16 × Desired_Frequency)
```

For 2 MHz clock:
```
Period = 2,000,000 / (16 × frequency_in_Hz)
```

**Common Notes:**
- Middle C (262 Hz): Period = 477 (0x01DD)
- A440 (440 Hz): Period = 284 (0x011C)
- C5 (523 Hz): Period = 238 (0x00EE)

## Architecture

The emulator consists of three main components:

### 1. CPU8051 (`cpu8051.py`)
- Complete 8051 instruction set emulator
- Handles all standard opcodes
- Manages interrupts (especially UART)
- Provides port I/O for AY-3-8910 control

### 2. AY3910Audio (`ay3910_audio.py`)
- Emulates AY-3-8910 registers and tone generators
- Generates real-time audio samples
- Provides audio output via PyAudio
- Supports 3 channels with independent frequency and amplitude control

### 3. SoundSystem (`main.py`)
- Connects CPU to sound chip
- Handles Port 1 (data bus) and Port 3 (control signals)
- Manages UART input from stdin
- Coordinates CPU execution with audio generation

## How It Works

1. **Firmware Execution**: The 8051 CPU executes the actual `sound_cpu_8051.bin` firmware
2. **UART Reception**: Commands entered via stdin are received by the 8051's UART
3. **Command Processing**: The firmware's interrupt handler parses the command protocol
4. **AY Control**: The firmware writes to Port 1 and Port 3 to control the AY-3-8910
5. **Audio Generation**: The AY chip generates audio samples based on register settings
6. **Audio Output**: PyAudio plays the generated samples in real-time

## Example Session

```bash
$ python3 main.py
Loading ROM: ../sound_cpu_8051.bin
============================================================
8051 + AY-3-8910 Sound System Emulator
============================================================

Audio output started
System started!

UART input ready (stdin)
Paste hex bytes (e.g., B5 A4 00 DD 01 0F B0) or type 'q' to quit

B5 A4 00 DD 01 0F B0
Sent 7 bytes to UART

status
AY-3-8910 State:
============================================================
Channel A:
  Period:  477 (0x1DD)
  Frequency:  262.05 Hz
  Amplitude: 15 (0x0F)
  Tone: ON, Noise: OFF
Channel B:
  Period:    0 (0x000)
  Frequency:    0.00 Hz
  Amplitude:  0 (0x00)
  Tone: OFF, Noise: OFF
Channel C:
  Period:    0 (0x000)
  Frequency:    0.00 Hz
  Amplitude:  0 (0x00)
  Tone: OFF, Noise: OFF
============================================================

q
Quitting...
Stopping system...
Audio output stopped
System stopped
```

## Troubleshooting

### No Audio Output

If you see "PyAudio not available", install it:
```bash
pip install pyaudio
```

### Import Errors

Make sure you're running from the emulator directory:
```bash
cd emulator
python3 main.py
```

### High CPU Usage

The emulator runs at full speed to match the 8051's execution rate. This is normal behavior.

## Technical Details

### 8051 CPU Specifications
- Clock: Variable (synced with audio generation)
- Internal RAM: 256 bytes
- External RAM: 64KB
- ROM: 32KB (sound_cpu_8051.bin)

### AY-3-8910 Specifications
- Clock: 2 MHz (default)
- Channels: 3 (A, B, C)
- Frequency Range: ~30 Hz to 125 kHz
- Amplitude: 16 levels (0-15)
- Sample Rate: 44.1 kHz (default)

### Port Connections
- **Port 1 (0x90)**: 8-bit data/address bus to AY-3-8910
- **Port 3 (0xB0)**: Control signals
  - P3.0: BC1 (Bus Control 1)
  - P3.4: BDIR (Bus Direction)
  - P3.5: BC2 (Bus Control 2)

## License

This emulator is provided for educational and compatibility purposes.

## See Also

- `../COMMAND_PROTOCOL.md` - Complete protocol specification
- `../ARCHITECTURE.txt` - System architecture diagram
- `../emulator_reference.py` - High-level reference implementation
- `../command_generator.py` - Generate test commands
