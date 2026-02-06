#!/usr/bin/env python3
"""
Detailed Command Protocol Analysis
Focuses on UART command handling and AY-3-8910 control
"""

import sys

def load_binary(filename):
    """Load the binary file"""
    with open(filename, 'rb') as f:
        return bytearray(f.read())

def analyze_uart_handler(data):
    """Deep analysis of UART interrupt handler"""
    print("=" * 80)
    print("DETAILED UART HANDLER ANALYSIS")
    print("=" * 80)
    
    # UART handler is at 0x0445
    print("\n1. UART Interrupt Handler (0x0445):")
    print("   - Saves context (PSW, ACC, R0, R1, etc.)")
    print("   - Checks bit 0x99 (RI/TI flag)")
    print("   - Calls 0x0470 for receive handling")
    print("   - Sets bit 0x0C when data received")
    
    print("\n2. UART Receive Handler (0x0470):")
    print("   - At 0x048C: MOV A,SBUF (read UART data)")
    print("   - At 0x048E: CJNE A,#0xB5,... (compare with 0xB5)")
    print("   - At 0x0493: CJNE A,#0xB6,... (compare with 0xB6)")
    print("   - 0xB5 and 0xB6 appear to be START command markers!")
    
    print("\n3. Command Bytes Found:")
    print("   - 0xB5, 0xB6: Start markers (stored at 0x004F)")
    print("   - 0xB0: Some kind of END or special marker (at 0x01AB)")
    print("   - 0xA0: Command type (at 0x00B6)")
    print("   - 0xA2, 0xA3: Subtypes (at 0x00FE, 0x010A)")
    print("   - 0xA4-0xA6: More command types")
    print("   - 0xA7: Command at 0x0140")
    print("   - 0xA8: Command at 0x01C1")

def analyze_command_processing(data):
    """Analyze command processing logic"""
    print("\n" + "=" * 80)
    print("COMMAND PROCESSING FLOW")
    print("=" * 80)
    
    # Main command loop appears to be around 0x00C0 - 0x0360
    print("\n1. Main Loop (0x0098 - 0x00C0):")
    print("   - Waits for UART data (bit 0x04 flag)")
    print("   - Calls command parser")
    
    print("\n2. Command Parser (0x00C0 onwards):")
    print("   - Reads from buffer at 0x0050 (first byte)")
    print("   - Reads from buffer at 0x004F (command type)")
    print("   - At 0x00E0: Processes command bytes")
    
    # Analyze the command dispatch table
    print("\n3. Command Dispatch Analysis:")
    
    # Look at addresses where commands are compared
    commands = {
        0xA0: ("0x00B6", "Basic command - status?"),
        0xA2: ("0x00FE", "Subcommand - frequency low?"),
        0xA3: ("0x010A", "Subcommand - frequency high?"),
        0xA4: ("0x0110", "Subcommand - multi-byte (frequency + amplitude)"),
        0xA6: ("0x013A", "Stop/Reset command"),
        0xA7: ("0x0140", "Special command"),
        0xA8: ("0x01C1", "Another special command"),
        0xB0: ("0x01AB", "End marker"),
    }
    
    for cmd, (addr, desc) in commands.items():
        print(f"   0x{cmd:02X}: {desc:30s} handled near {addr}")
    
    # Show command format patterns
    print("\n4. Command Format Patterns:")
    print("   Pattern 1: [0xB5/0xB6] [0xA0] [data]")
    print("   Pattern 2: [0xB5/0xB6] [0xA2] [channel] [freq_low]")
    print("   Pattern 3: [0xB5/0xB6] [0xA3] [channel] [freq_high]")
    print("   Pattern 4: [0xB5/0xB6] [0xA4] [channel] [freq_low] [freq_high] [amplitude]")
    print("   Pattern 5: [0xB5/0xB6] [0xA6] - Stop")
    print("   End: [0xB0]")

def analyze_ay3891_control(data):
    """Analyze AY-3-8910 control sequences"""
    print("\n" + "=" * 80)
    print("AY-3-8910 CONTROL ANALYSIS")
    print("=" * 80)
    
    print("\nAY-3-8910 Interface:")
    print("  - Port P1 (0x90) = 8-bit data/address bus")
    print("  - Port P3 bits used for control signals:")
    print("    - P3.0 (B0/0xB0 bit): BC1 (Bus Control 1)")
    print("    - P3.4 (B4/0xB4 bit): BDIR (Bus Direction)")
    print("    - P3.5 (B5/0xB5 bit): BC2 (Bus Control 2)")
    
    print("\n  Control combinations:")
    print("    BDIR BC2 BC1 | Function")
    print("    -------------------------")
    print("       0   1   0 | Inactive")
    print("       0   1   1 | Read from PSG")
    print("       1   1   0 | Write to PSG")
    print("       1   1   1 | Latch address")
    
    # Find key functions
    print("\n  Key Functions:")
    
    # Function at 0x05A6 - AY register write setup
    print("\n  1. AY Register Write Function (around 0x05A6):")
    print("     - Sets P1 to 0x0F (address latch mode)")
    print("     - Then sets P1 to 0xFF")
    print("     - Writes register address then data")
    
    # Function at 0x05E6 - appears to be another control
    print("\n  2. AY Control Function (around 0x05E6):")
    print("     - Sets P1 to 0x0E (write mode)")
    
    # Look at initialization
    print("\n  3. Initialization (0x0026):")
    print("     - Sets Stack Pointer to 0x57")
    print("     - Disables interrupts initially")
    print("     - Sets P1 to 0xFF (idle state)")

def analyze_memory_map(data):
    """Analyze memory usage and buffer locations"""
    print("\n" + "=" * 80)
    print("MEMORY MAP ANALYSIS")
    print("=" * 80)
    
    print("\nKey Memory Locations:")
    print("  0x004B: Command state machine step counter")
    print("  0x004F: Command type/marker (0xB5 or 0xB6)")
    print("  0x0050: Command data buffer start")
    print("  0x006E: Status/control byte")
    print("  0x006F: Another status byte")
    print("  0x0070: Yet another status byte")
    print("  0x0072: Data storage")
    print("  0x0073: Data storage")
    print("  0x007D: Extended buffer area")
    
    print("\nSFR Bit Flags Used:")
    print("  bit 0x04: UART data ready flag")
    print("  bit 0x09: General status flag")
    print("  bit 0x0B: Processing flag")
    print("  bit 0x0C: UART receive complete flag")
    print("  bit 0x0D: Command active flag")
    print("  bit 0xB2: REN (UART Receive Enable)")
    print("  bit 0xB3: TB8 (UART Transmit bit)")

def extract_command_table(data):
    """Extract command lookup tables from the binary"""
    print("\n" + "=" * 80)
    print("COMMAND LOOKUP TABLES")
    print("=" * 80)
    
    # There appear to be lookup tables around 0x0622, 0x27AC, etc.
    print("\nTable at 0x0622:")
    for i in range(0x0622, min(0x0640, len(data))):
        print(f"  0x{i:04X}: 0x{data[i]:02X}")
    
    # Another table reference at 0x27AC (seen in 0x02FA)
    if len(data) > 0x27AC:
        print("\nTable at 0x27AC (freq/note table?):")
        for i in range(0x27AC, min(0x27C0, len(data))):
            print(f"  0x{i:04X}: 0x{data[i]:02X}")

def extract_detailed_code_flow(data):
    """Trace through key code paths"""
    print("\n" + "=" * 80)
    print("DETAILED CODE FLOW TRACE")
    print("=" * 80)
    
    print("\nCommand Reception Flow:")
    print("  1. UART interrupt fires (0x0445)")
    print("  2. Handler checks RI flag (bit 0x99)")
    print("  3. Calls receive handler (0x0470)")
    print("  4. Reads SBUF (0x048C)")
    print("  5. Checks for 0xB5 or 0xB6 start marker")
    print("  6. If match, stores at 0x004F, sets state to 1 at 0x004B")
    print("  7. Returns from interrupt")
    print("")
    print("  8. Main loop checks bit 0x04 flag")
    print("  9. Calls command processing (around 0x00C0)")
    print(" 10. Reads buffer at 0x0050 (data bytes)")
    print(" 11. Checks command type from 0x004F")
    print(" 12. Dispatches to appropriate handler")
    print("")
    print(" Command Handlers:")
    print("  - 0xA0: Simple status/control")
    print("  - 0xA2: Set frequency low byte for channel")
    print("  - 0xA3: Set frequency high byte for channel")
    print("  - 0xA4: Multi-byte: channel + freq + amplitude")
    print("  - 0xA6: Stop/silence")
    print("")
    print(" 13. Handler writes to AY-3-8910 via Port P1")
    print(" 14. Waits for 0xB0 end marker or continues")

def main():
    filename = "/home/runner/work/Mephisto/Mephisto/sound_cpu_8051.bin"
    data = load_binary(filename)
    
    analyze_uart_handler(data)
    analyze_command_processing(data)
    analyze_ay3891_control(data)
    analyze_memory_map(data)
    extract_command_table(data)
    extract_detailed_code_flow(data)
    
    print("\n" + "=" * 80)
    print("CONCLUSION & COMMAND PROTOCOL SUMMARY")
    print("=" * 80)
    
    print("""
COMMAND PROTOCOL IDENTIFIED:

1. Start Byte: 0xB5 or 0xB6
   - These mark the beginning of a command sequence
   - Stored at memory location 0x004F

2. Command Byte (one of):
   - 0xA0: Status/Control command
   - 0xA2: Set frequency low byte
   - 0xA3: Set frequency high byte
   - 0xA4: Set full note (4+ bytes: channel, freq_low, freq_high, amplitude)
   - 0xA6: Stop/Reset command
   - 0xA7: Special command
   - 0xA8: Another special command

3. Data Bytes (vary by command):
   - For 0xA2/0xA3: [channel] [value]
   - For 0xA4: [channel] [freq_low] [freq_high] [amplitude]
   - Channel appears to be: 0=A, 1=B, 2=C (3 channels in AY-3-8910)

4. End Byte: 0xB0
   - Marks end of command or sequence

TYPICAL COMMAND SEQUENCES:

Play Note on Channel:
  [0xB5/0xB6] [0xA4] [channel] [freq_low] [freq_high] [amplitude] [0xB0]

Or split commands:
  [0xB5/0xB6] [0xA2] [channel] [freq_low] [0xB0]
  [0xB5/0xB6] [0xA3] [channel] [freq_high] [0xB0]

Stop All:
  [0xB5/0xB6] [0xA6] [0xB0]

AY-3-8910 Register Mapping:
  - Registers 0-5: Tone periods (3 channels, 2 bytes each)
  - Registers 6: Noise period
  - Register 7: Mixer control
  - Registers 8-10: Amplitude (3 channels)
  - Registers 11-13: Envelope
""")

if __name__ == "__main__":
    main()
