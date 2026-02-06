# Quick Reference Card - 8051 Sound CPU Protocol

## Command Format
```
[START] [CMD] [DATA...] [END]
```

## Essential Bytes
| Byte | Purpose | Value(s) |
|------|---------|----------|
| START | Begin command | 0xB5 or 0xB6 |
| END | Finish command | 0xB0 |

## Commands

### 0xA4 - Play Note (Most Common)
```
B5 A4 [CH] [FL] [FH] [AMP] B0
```
- **CH**: Channel (0=A, 1=B, 2=C)
- **FL**: Frequency low byte (0-255)
- **FH**: Frequency high byte (0-15)
- **AMP**: Amplitude/volume (0-15)

**Example:** Middle C on channel A
```
B5 A4 00 DD 01 0F B0
```

### 0xA2 - Set Frequency Low Byte
```
B6 A2 [CH] [VAL] B0
```

### 0xA3 - Set Frequency High Byte
```
B5 A3 [CH] [VAL] B0
```

### 0xA6 - Stop All Channels
```
B5 A6 B0
```

## Frequency Calculation

**Formula:**
```
Period = 2,000,000 / (16 × Hz)
```

**Common Notes:**
| Note | Hz  | Period | Hex  | Low | High |
|------|-----|--------|------|-----|------|
| C3   | 131 | 955    | 03BB | BB  | 03   |
| C4   | 262 | 477    | 01DD | DD  | 01   |
| E4   | 330 | 379    | 017B | 7B  | 01   |
| G4   | 392 | 318    | 013E | 3E  | 01   |
| A4   | 440 | 284    | 011C | 1C  | 01   |
| C5   | 523 | 238    | 00EE | EE  | 00   |

## Python Quick Start

```python
from emulator_reference import SoundSystemEmulator

# Create emulator
emu = SoundSystemEmulator()

# Play note (easy way)
emu.play_note(channel=0, frequency_hz=440, amplitude=15)

# Send raw command (manual way)
emu.uart_send_bytes([0xB5, 0xA4, 0x00, 0x1C, 0x01, 0x0F, 0xB0])
emu.process()

# Check state
print(emu.get_ay_state())

# Stop all
emu.stop_all()
```

## Common Command Sequences

### Play Chord (C Major)
```python
# C4 on channel A
emu.uart_send_bytes([0xB5, 0xA4, 0x00, 0xDD, 0x01, 0x0C, 0xB0])
# E4 on channel B
emu.uart_send_bytes([0xB5, 0xA4, 0x01, 0x7B, 0x01, 0x0C, 0xB0])
# G4 on channel C
emu.uart_send_bytes([0xB5, 0xA4, 0x02, 0x3E, 0x01, 0x0C, 0xB0])
emu.process_all()
```

### Scale (C4 to C5)
```python
notes = [
    [0xB5, 0xA4, 0x00, 0xDD, 0x01, 0x0C, 0xB0],  # C4
    [0xB5, 0xA4, 0x00, 0xA9, 0x01, 0x0C, 0xB0],  # D4
    [0xB5, 0xA4, 0x00, 0x7B, 0x01, 0x0C, 0xB0],  # E4
    [0xB5, 0xA4, 0x00, 0x65, 0x01, 0x0C, 0xB0],  # F4
    [0xB5, 0xA4, 0x00, 0x3E, 0x01, 0x0C, 0xB0],  # G4
    [0xB5, 0xA4, 0x00, 0x1C, 0x01, 0x0C, 0xB0],  # A4
    [0xB5, 0xA4, 0x00, 0xFD, 0x00, 0x0C, 0xB0],  # B4
    [0xB5, 0xA4, 0x00, 0xEE, 0x00, 0x0C, 0xB0],  # C5
]
for note in notes:
    emu.uart_send_bytes(note)
    emu.process()
```

## Hardware Testing

### Via Serial Terminal
```bash
# Set baud rate (check firmware for actual rate)
stty -F /dev/ttyUSB0 9600

# Send test command (in hex)
echo -ne '\xB5\xA4\x00\xDD\x01\x0F\xB0' > /dev/ttyUSB0
```

### Via Python Serial
```python
import serial

ser = serial.Serial('/dev/ttyUSB0', 9600)

# Play middle C
ser.write(bytes([0xB5, 0xA4, 0x00, 0xDD, 0x01, 0x0F, 0xB0]))

# Stop all
ser.write(bytes([0xB5, 0xA6, 0xB0]))

ser.close()
```

## Troubleshooting

### No Sound?
1. Check start byte (0xB5 or 0xB6)
2. Check end byte (0xB0)
3. Verify amplitude > 0
4. Verify channel number (0-2)

### Wrong Frequency?
1. Check period calculation
2. Verify high/low byte order
3. Test with known values (e.g., A440 = 0x011C)

### Command Ignored?
1. Ensure proper start marker
2. Check for end marker
3. Verify no extra bytes between commands

## Memory Addresses (for debugging)

| Address | Description |
|---------|-------------|
| 0x004B | State counter |
| 0x004F | Start marker |
| 0x0050 | Data buffer |
| 0x0445 | UART ISR |

## Generate Commands

Use the command generator:
```bash
python3 command_generator.py
```

Or in Python:
```python
from command_generator import generate_note_command

# Generate command for A4 on channel 0
cmd = generate_note_command(0, "A4", 12)
print(' '.join(f'{b:02X}' for b in cmd))
# Output: B5 A4 00 1C 01 0C B0
```

## AY-3-8910 Channels

| Channel | Number | Description |
|---------|--------|-------------|
| A | 0 | First voice |
| B | 1 | Second voice |
| C | 2 | Third voice |

All three channels can play simultaneously!

## Amplitude Levels

| Value | Level |
|-------|-------|
| 0x00 | Silent |
| 0x08 | Half |
| 0x0C | 3/4 |
| 0x0F | Max |

## Files to Use

| Task | File |
|------|------|
| Understand protocol | COMMAND_PROTOCOL.md |
| Emulate system | emulator_reference.py |
| Generate commands | command_generator.py |
| See internals | REVERSE_ENGINEERING_REPORT.md |

---
**Quick Test:**
```python
python3 emulator_reference.py  # Runs demo
```

**Status:** ✅ Protocol fully documented and tested
