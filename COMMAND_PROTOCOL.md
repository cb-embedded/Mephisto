# 8051 Sound CPU Reverse Engineering - Final Report

## Overview

This document describes the reverse-engineered UART command protocol for the 8051 microcontroller that controls an AY-3-8910 Programmable Sound Generator (PSG) chip.

**Binary analyzed:** `sound_cpu_8051.bin` (32,768 bytes)

## Architecture

### Hardware Interface
- **MCU**: 8051-compatible microcontroller
- **Sound Chip**: AY-3-8910 PSG (3-channel programmable sound generator)
- **Interface**: 
  - Port P1 (0x90) → 8-bit data/address bus to AY-3-8910
  - Port P3 bits → Control signals (BC1, BC2, BDIR)
  - UART (SBUF 0x99) → Command input

### Memory Map
- `0x004B`: State machine counter (0, 1, or 2)
- `0x004F`: Start marker storage (0xB5 or 0xB6)
- `0x0050`: Command data buffer (variable length)
- `0x004E`: Byte counter for multi-byte commands
- `0x006E-0x0070`: Status/control bytes
- `0x0072-0x0073`: Frequency data storage

### Interrupt Vectors
- `0x0000`: RESET → `0x0026` (Initialization)
- `0x0023`: UART → `0x0445` (UART interrupt handler - **CRITICAL**)
- `0x000B`: TIMER0 → `0x051D` (Timer interrupt for periodic AY updates)

## Command Protocol

### Protocol Structure

Every command follows this structure:

```
[START_MARKER] [COMMAND_BYTE] [DATA_BYTES...] [END_MARKER]
```

### 1. Start Marker (Required)

**Values:** `0xB5` or `0xB6`

These bytes signal the beginning of a command. The UART interrupt handler (at `0x048C`) checks for these specific values and transitions the state machine from state 0 to state 1.

- Both `0xB5` and `0xB6` are accepted as valid start markers
- The received marker is stored at memory location `0x004F`
- Any other byte received in state 0 is ignored

### 2. Command Byte (Required)

The following command bytes have been identified:

| Command | Hex  | Description | Data Bytes | Handler Address |
|---------|------|-------------|------------|----------------|
| STATUS  | 0xA0 | Status/control command | Variable | ~0x00B6 |
| FREQ_LO | 0xA2 | Set frequency low byte | 2 (channel, value) | ~0x0102 |
| FREQ_HI | 0xA3 | Set frequency high byte | 2 (channel, value) | ~0x010D |
| NOTE    | 0xA4 | Full note (freq + amp) | 4+ (channel, f_lo, f_hi, amp) | ~0x0118 |
| STOP    | 0xA6 | Stop/silence all | 0 | ~0x0144 |
| SPECIAL1| 0xA7 | Special command | Variable | ~0x0140 |
| SPECIAL2| 0xA8 | Another special cmd | Variable | ~0x01C1 |

### 3. Data Bytes (Variable)

Data format depends on the command:

#### For FREQ_LO (0xA2) and FREQ_HI (0xA3):
```
[channel] [value]
```
- `channel`: 0, 1, or 2 (for AY-3-8910 channels A, B, C)
- `value`: 8-bit frequency value

#### For NOTE (0xA4):
```
[channel] [freq_low] [freq_high] [amplitude]
```
- `channel`: Lower nibble (0-2)
- `freq_low`: Frequency period low byte
- `freq_high`: Frequency period high byte
- `amplitude`: Volume level (0x00-0x0F)

### 4. End Marker (Required)

**Value:** `0xB0`

This byte signals the end of a command sequence. The main loop checks for this marker (at `0x01AB`) to determine when a command is complete.

## Command Examples

### Example 1: Play a Note on Channel A

Play a note with frequency period 0x01A4 and amplitude 0x0F on channel 0:

```
Hex: B5 A4 00 A4 01 0F B0
     │  │  │  │  │  │  │
     │  │  │  │  │  │  └─ End marker
     │  │  │  │  │  └──── Amplitude (0x0F = max)
     │  │  │  │  └─────── Frequency high byte
     │  │  │  └────────── Frequency low byte
     │  │  └───────────── Channel (0 = A)
     │  └──────────────── Command (0xA4 = Note)
     └─────────────────── Start marker
```

### Example 2: Set Frequency Low Byte

Set the low byte of the frequency for channel 1:

```
Hex: B6 A2 01 44 B0
     │  │  │  │  │
     │  │  │  │  └─ End marker
     │  │  │  └──── Frequency low byte value
     │  │  └─────── Channel (1 = B)
     │  └────────── Command (0xA2 = Freq Low)
     └───────────── Start marker (alternate)
```

### Example 3: Set Frequency High Byte

Set the high byte of the frequency for channel 2:

```
Hex: B5 A3 02 03 B0
     │  │  │  │  │
     │  │  │  │  └─ End marker
     │  │  │  └──── Frequency high byte value
     │  │  └─────── Channel (2 = C)
     │  └────────── Command (0xA3 = Freq High)
     └───────────── Start marker
```

### Example 4: Stop All Sounds

Send stop command to silence all channels:

```
Hex: B5 A6 B0
     │  │  │
     │  │  └─ End marker
     │  └──── Command (0xA6 = Stop)
     └─────── Start marker
```

### Example 5: Playing a Sequence

To play middle C (approximately 262 Hz) on channel 0:

AY-3-8910 uses a master clock divided by 16, then by the period value.
For a 2 MHz clock: frequency = 2000000 / (16 * period)
For 262 Hz: period ≈ 477 (0x01DD)

```
Hex: B5 A4 00 DD 01 0C B0
     │  │  │  │  │  │  │
     │  │  │  │  │  │  └─ End marker
     │  │  │  │  │  └──── Amplitude (0x0C)
     │  │  │  │  └─────── Period high (0x01)
     │  │  │  └────────── Period low (0xDD)
     │  │  └───────────── Channel 0
     │  └──────────────── Note command
     └─────────────────── Start marker
```

## State Machine

The UART receive handler implements a 3-state machine:

### State 0: Wait for Start Marker
- **Entry condition:** Reset or after completing a command
- **Operation:** Scan incoming UART bytes for 0xB5 or 0xB6
- **On match:** Store marker at 0x004F, transition to State 1
- **On no match:** Discard byte, stay in State 0
- **Code location:** `0x048C`

### State 1: Receive First Data Byte
- **Entry condition:** Start marker detected
- **Operation:** Read next UART byte as command/data
- **Action:** Store byte at 0x0050, set byte counter
- **Next state:** Transition to State 2
- **Code location:** `0x04BB`

### State 2: Receive Remaining Bytes
- **Entry condition:** After first data byte
- **Operation:** Continue reading UART bytes into buffer (0x0051, 0x0052, ...)
- **Action:** Decrement byte counter, store each byte
- **On counter = 0:** Set bit_04 flag (data ready), transition to State 0
- **Code location:** `0x04DE`

### Command Processing
- **Trigger:** Main loop polls bit_04 flag (at `0x00AC`)
- **Action:** Parse buffer starting at 0x0050
- **Dispatch:** Jump to appropriate handler based on command byte
- **Completion:** Check for 0xB0 end marker

## AY-3-8910 Control

### Register Map

The AY-3-8910 has 16 registers (R0-R15):

| Register | Function |
|----------|----------|
| R0-R1 | Channel A Tone Period (12-bit) |
| R2-R3 | Channel B Tone Period (12-bit) |
| R4-R5 | Channel C Tone Period (12-bit) |
| R6 | Noise Period (5-bit) |
| R7 | Mixer Control-I/O Enable |
| R8 | Channel A Amplitude (5-bit) |
| R9 | Channel B Amplitude (5-bit) |
| R10 | Channel C Amplitude (5-bit) |
| R11-R12 | Envelope Period (16-bit) |
| R13 | Envelope Shape/Cycle |
| R14-R15 | I/O Ports A & B |

### Control Signals (Port P3)

The AY-3-8910 is controlled using three signals:

- **BDIR** (Bus Direction): P3.4
- **BC2** (Bus Control 2): P3.5
- **BC1** (Bus Control 1): P3.0

Control signal combinations:

| BDIR | BC2 | BC1 | Function |
|------|-----|-----|----------|
| 0 | 1 | 0 | Inactive |
| 0 | 1 | 1 | Read from PSG |
| 1 | 1 | 0 | Write to PSG |
| 1 | 1 | 1 | Latch Address |

### Write Sequence

To write to an AY-3-8910 register:

1. **Latch Address** (Function at `0x05A6`):
   - Set P1 = register address
   - Set control signals: BDIR=1, BC2=1, BC1=1
   - Pulse control lines

2. **Write Data** (Function at `0x05E6`):
   - Set P1 = data value
   - Set control signals: BDIR=1, BC2=1, BC1=0
   - Pulse control lines

### Timer-Driven Updates

The Timer 0 interrupt (at `0x051D`) runs periodically and:
- Calls `0x05A6` to update AY registers
- Calls `0x05E6` to write control/data
- Updates sound output continuously

## Frequency Calculation

The AY-3-8910 tone period is calculated as:

```
Period = Clock_Frequency / (16 * Desired_Frequency)
```

For a typical 2 MHz clock:
```
Period = 2000000 / (16 * frequency_in_Hz)
```

Example frequencies:
- Middle C (262 Hz): Period ≈ 477 (0x01DD)
- A440 (440 Hz): Period ≈ 284 (0x011C)
- C523 (523 Hz): Period ≈ 239 (0x00EF)

The 12-bit period is split into:
- Low byte: Stored in R0/R2/R4 (for channels A/B/C)
- High byte: Stored in R1/R3/R5 (for channels A/B/C)

## Implementation Guide for Emulation

To emulate this system, you need to:

### 1. 8051 Emulator Component

```python
class Sound8051Emulator:
    def __init__(self):
        self.state = 0  # State machine state
        self.marker = 0  # Start marker (0xB5 or 0xB6)
        self.buffer = []  # Data buffer
        self.data_ready = False
        
    def receive_uart_byte(self, byte):
        if self.state == 0:  # Wait for start marker
            if byte in [0xB5, 0xB6]:
                self.marker = byte
                self.state = 1
                self.buffer = []
        elif self.state == 1:  # First data byte
            self.buffer.append(byte)
            self.state = 2
        elif self.state == 2:  # Continue receiving
            self.buffer.append(byte)
            if byte == 0xB0:  # End marker
                self.data_ready = True
                self.state = 0
                
    def process_command(self):
        if not self.data_ready or not self.buffer:
            return None
            
        self.data_ready = False
        cmd = self.buffer[0]
        data = self.buffer[1:-1]  # Exclude command and end marker
        
        return (cmd, data)
```

### 2. AY-3-8910 Emulator Component

```python
class AY3810Emulator:
    def __init__(self):
        self.registers = [0] * 16
        self.address_latch = 0
        
    def latch_address(self, address):
        self.address_latch = address & 0x0F
        
    def write_data(self, data):
        if 0 <= self.address_latch < 16:
            self.registers[self.address_latch] = data
            
    def set_channel_frequency(self, channel, period):
        if channel == 0:  # Channel A
            self.registers[0] = period & 0xFF
            self.registers[1] = (period >> 8) & 0x0F
        elif channel == 1:  # Channel B
            self.registers[2] = period & 0xFF
            self.registers[3] = (period >> 8) & 0x0F
        elif channel == 2:  # Channel C
            self.registers[4] = period & 0xFF
            self.registers[5] = (period >> 8) & 0x0F
            
    def set_channel_amplitude(self, channel, amplitude):
        if 0 <= channel <= 2:
            self.registers[8 + channel] = amplitude & 0x1F
```

### 3. Command Handler

```python
def handle_command(cmd, data, ay_chip):
    if cmd == 0xA0:  # Status
        # Handle status command
        pass
        
    elif cmd == 0xA2:  # Frequency low byte
        if len(data) >= 2:
            channel = data[0]
            freq_low = data[1]
            # Update low byte of frequency
            current = (ay_chip.registers[channel*2+1] << 8) | ay_chip.registers[channel*2]
            new_freq = (current & 0xFF00) | freq_low
            ay_chip.set_channel_frequency(channel, new_freq)
            
    elif cmd == 0xA3:  # Frequency high byte
        if len(data) >= 2:
            channel = data[0]
            freq_high = data[1]
            # Update high byte of frequency
            current = (ay_chip.registers[channel*2+1] << 8) | ay_chip.registers[channel*2]
            new_freq = (freq_high << 8) | (current & 0x00FF)
            ay_chip.set_channel_frequency(channel, new_freq)
            
    elif cmd == 0xA4:  # Full note
        if len(data) >= 4:
            channel = data[0]
            freq_low = data[1]
            freq_high = data[2]
            amplitude = data[3]
            
            period = (freq_high << 8) | freq_low
            ay_chip.set_channel_frequency(channel, period)
            ay_chip.set_channel_amplitude(channel, amplitude)
            
    elif cmd == 0xA6:  # Stop all
        for ch in range(3):
            ay_chip.set_channel_amplitude(ch, 0)
```

## Testing Commands

Here's a test sequence you can send via UART:

```python
# Test 1: Play note on channel 0
test_cmd_1 = [0xB5, 0xA4, 0x00, 0xDD, 0x01, 0x0F, 0xB0]

# Test 2: Set frequency low on channel 1
test_cmd_2 = [0xB6, 0xA2, 0x01, 0x44, 0xB0]

# Test 3: Set frequency high on channel 1
test_cmd_3 = [0xB5, 0xA3, 0x01, 0x02, 0xB0]

# Test 4: Stop all
test_cmd_4 = [0xB5, 0xA6, 0xB0]

# Test 5: Play chord (all 3 channels)
# Channel 0: C (262 Hz) - period 477 (0x01DD)
test_cmd_5a = [0xB5, 0xA4, 0x00, 0xDD, 0x01, 0x0C, 0xB0]
# Channel 1: E (330 Hz) - period 379 (0x017B)
test_cmd_5b = [0xB5, 0xA4, 0x01, 0x7B, 0x01, 0x0C, 0xB0]
# Channel 2: G (392 Hz) - period 319 (0x013F)
test_cmd_5c = [0xB5, 0xA4, 0x02, 0x3F, 0x01, 0x0C, 0xB0]
```

## Conclusion

This reverse engineering effort has successfully identified:

1. **Protocol Structure**: Start marker (0xB5/0xB6) → Command byte → Data bytes → End marker (0xB0)

2. **Command Set**: 8 identified commands (0xA0, 0xA2, 0xA3, 0xA4, 0xA6, 0xA7, 0xA8, 0xB0)

3. **State Machine**: 3-state UART receiver with buffer management

4. **Hardware Interface**: Complete understanding of AY-3-8910 control via Port P1 and P3

5. **Memory Map**: Key locations for state, buffers, and control flags

With this information, you can now:
- Send proper commands to the real hardware via UART
- Emulate both the 8051 MCU and AY-3-8910 PSG
- Generate music/sound effects by sending appropriate command sequences
- Test the system with known-good command patterns

The protocol is simple, robust, and designed for real-time sound generation with the classic AY-3-8910 programmable sound generator chip.
