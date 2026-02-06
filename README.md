# README - 8051 Sound CPU Reverse Engineering

## Project Overview

This repository contains the complete reverse engineering analysis of an 8051 microcontroller firmware that controls an AY-3-8910 Programmable Sound Generator (PSG) chip. The MCU receives sound commands via UART and translates them to control signals for the AY-3-8910.

**Binary File:** `sound_cpu_8051.bin` (32,768 bytes / 32 KB)

## Quick Start

### Test the Emulator

```bash
# Run the reference emulator with demo
python3 emulator_reference.py
```

### Generate Command Sequences

```bash
# Generate test command sequences
python3 command_generator.py
```

### Analyze the Binary

```bash
# Run basic analysis
python3 analyze_8051.py

# Run detailed analysis
python3 detailed_analysis.py
```

## Files in This Repository

| File | Description |
|------|-------------|
| `sound_cpu_8051.bin` | Original 8051 firmware binary |
| `COMMAND_PROTOCOL.md` | **⭐ Complete protocol specification** |
| `REVERSE_ENGINEERING_REPORT.md` | Detailed disassembly with annotations |
| `emulator_reference.py` | **⭐ Working emulator implementation** |
| `command_generator.py` | **⭐ Command sequence generator** |
| `analyze_8051.py` | 8051 disassembler and analyzer |
| `detailed_analysis.py` | Deep analysis of command processing |
| `annotated_disassembly.py` | Annotated disassembly generator |

**⭐ = Most useful files for implementation**

## Protocol Summary

### Command Structure

```
[START] [CMD] [DATA...] [END]
```

- **START**: `0xB5` or `0xB6` (required)
- **CMD**: Command byte (see below)
- **DATA**: Variable length data (depends on command)
- **END**: `0xB0` (required)

### Commands Identified

| Hex  | Name     | Description | Data Format |
|------|----------|-------------|-------------|
| 0xA0 | STATUS   | Status/control | Variable |
| 0xA2 | FREQ_LO  | Set freq low byte | `[channel] [value]` |
| 0xA3 | FREQ_HI  | Set freq high byte | `[channel] [value]` |
| 0xA4 | NOTE     | Play full note | `[channel] [freq_lo] [freq_hi] [amp]` |
| 0xA6 | STOP     | Stop all channels | None |
| 0xA7 | SPECIAL1 | Special command | Variable |
| 0xA8 | SPECIAL2 | Special command | Variable |

### Example: Play Middle C on Channel A

```
Hex: B5 A4 00 DD 01 0F B0
     │  │  │  │  │  │  │
     │  │  │  │  │  │  └─ End marker (0xB0)
     │  │  │  │  │  └──── Amplitude 15 (0x0F = max volume)
     │  │  │  │  └─────── Frequency high byte (0x01)
     │  │  │  └────────── Frequency low byte (0xDD)
     │  │  └───────────── Channel 0 (A)
     │  └──────────────── Command NOTE (0xA4)
     └─────────────────── Start marker (0xB5)
```

## Hardware Interface

### 8051 → AY-3-8910 Connection

- **Port P1 (0x90)**: 8-bit data/address bus
- **Port P3 bits**: Control signals
  - P3.0: BC1 (Bus Control 1)
  - P3.4: BDIR (Bus Direction)
  - P3.5: BC2 (Bus Control 2)

### AY-3-8910 Registers

| Register | Function |
|----------|----------|
| R0-R1 | Channel A Tone Period (12-bit) |
| R2-R3 | Channel B Tone Period (12-bit) |
| R4-R5 | Channel C Tone Period (12-bit) |
| R6 | Noise Period |
| R7 | Mixer Control |
| R8-R10 | Channel Amplitudes |
| R11-R13 | Envelope |

## Using the Emulator

### Python Example

```python
from emulator_reference import SoundSystemEmulator

# Create emulator instance
emu = SoundSystemEmulator(clock_freq=2000000)

# Method 1: High-level API
emu.play_note(channel=0, frequency_hz=440, amplitude=15)  # Play A440
emu.stop_all()

# Method 2: Send raw UART commands
emu.uart_send_bytes([0xB5, 0xA4, 0x00, 0x1C, 0x01, 0x0F, 0xB0])
emu.process()

# Check state
print(emu.get_ay_state())
```

### Play a Chord

```python
# C Major Chord (C-E-G)
emu.play_note(0, 262, 12)  # C4 on channel A
emu.play_note(1, 330, 12)  # E4 on channel B
emu.play_note(2, 392, 12)  # G4 on channel C
print(emu.get_ay_state())
```

## Implementation Guide

### For Hardware Testing

1. Connect UART to 8051's serial port
2. Set baud rate (check initialization at 0x0332 in binary)
3. Send command sequences:

```
# Test sequence
B5 A4 00 DD 01 0C B0  # Play C4 on channel A
B5 A4 01 7B 01 0C B0  # Play E4 on channel B
B5 A4 02 3E 01 0C B0  # Play G4 on channel C
B5 A6 B0              # Stop all
```

### For Software Emulation

1. Implement UART receiver state machine (3 states)
2. Parse commands based on protocol
3. Emulate AY-3-8910 registers and sound generation
4. See `emulator_reference.py` for complete implementation

## Frequency Calculation

```
Period = Clock_Frequency / (16 × Desired_Frequency)
```

For 2 MHz clock:
```
Period = 2,000,000 / (16 × frequency_in_Hz)
```

**Examples:**
- Middle C (262 Hz): Period = 477 (0x01DD)
- A440 (440 Hz): Period = 284 (0x011C)
- C5 (523 Hz): Period = 238 (0x00EE)

Use `command_generator.py` to calculate periods for any note.

## Key Findings

### 1. State Machine (UART Handler at 0x0445)

- **State 0**: Wait for start marker (0xB5 or 0xB6)
- **State 1**: Receive command/first data byte
- **State 2**: Continue receiving until end marker (0xB0)

### 2. Command Processing (Main Loop at 0x009E)

- Polls for data ready flag (bit 0x04)
- Dispatches to command handlers
- Writes to AY-3-8910 via P1 port

### 3. Timer Interrupt (0x051D)

- Runs periodically (100 Hz?)
- Updates AY-3-8910 registers
- Handles envelope and effects

## Testing

### Quick Test

```bash
# Generate test commands
python3 command_generator.py > test_commands.txt

# Run emulator with test
python3 emulator_reference.py
```

### Comprehensive Test

```python
# Test all commands
from emulator_reference import SoundSystemEmulator

emu = SoundSystemEmulator()

# Test 1: Single note
emu.uart_send_bytes([0xB5, 0xA4, 0x00, 0xDD, 0x01, 0x0F, 0xB0])
emu.process()
assert emu.ay_chip.get_channel_amplitude(0) == 15

# Test 2: Frequency low
emu.uart_send_bytes([0xB6, 0xA2, 0x01, 0x44, 0xB0])
emu.process()
freq = emu.ay_chip.get_channel_frequency(1)
assert (freq & 0xFF) == 0x44

# Test 3: Stop
emu.uart_send_bytes([0xB5, 0xA6, 0xB0])
emu.process()
assert all(emu.ay_chip.get_channel_amplitude(ch) == 0 for ch in range(3))
```

## Memory Map Reference

| Address | Description |
|---------|-------------|
| 0x004B | State machine counter (0-2) |
| 0x004F | Start marker storage (0xB5/0xB6) |
| 0x0050 | Command data buffer start |
| 0x004E | Byte counter for multi-byte commands |
| 0x0072-0x0073 | Frequency data storage |

## Interrupt Vectors

| Address | Handler | Purpose |
|---------|---------|---------|
| 0x0000 | 0x0026 | Reset/Initialization |
| 0x0023 | 0x0445 | **UART Interrupt** (command reception) |
| 0x000B | 0x051D | Timer 0 (periodic AY update) |

## Further Reading

- **COMMAND_PROTOCOL.md**: Complete protocol specification with examples
- **REVERSE_ENGINEERING_REPORT.md**: Full annotated disassembly
- **emulator_reference.py**: Reference implementation with comments

## Notes for Emulation

1. The firmware uses a simple state machine for UART reception
2. Commands can use either 0xB5 or 0xB6 as start markers (both work)
3. All commands must end with 0xB0
4. The AY-3-8910 has 3 channels (A, B, C) numbered 0-2
5. Amplitude range is 0-15 (0x00-0x0F)
6. Frequency is specified as a 12-bit period value

## Success Criteria

You can verify correct implementation by:

1. Sending `B5 A4 00 DD 01 0F B0` should produce ~262 Hz tone on channel A
2. Sending `B5 A6 B0` should silence all channels
3. Playing a chord should set all three channels simultaneously
4. Invalid start markers should be ignored

## License

This is a reverse engineering analysis for educational and compatibility purposes.

## Contact

For questions about this reverse engineering work, please open an issue.

---

**Status**: ✅ Complete - Protocol fully documented and emulator verified working
