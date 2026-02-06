#!/usr/bin/env python3
"""
Enhanced Music Command Finder
Searches for music playback commands in the 8051 binary
"""

import sys

def load_binary(filename):
    with open(filename, 'rb') as f:
        return bytearray(f.read())

def find_music_commands(data):
    """Find commands related to music playback"""
    print("=" * 80)
    print("ENHANCED MUSIC COMMAND ANALYSIS")
    print("=" * 80)
    
    print("\n1. MUSIC DATA TABLES:")
    print("-" * 80)
    
    # Music sequences identified
    music_tables = {
        0x2D00: "Music sequence 1",
        0x2E00: "Music sequence 2", 
        0x2F00: "Music sequence 3",
        0x3000: "Music sequence 4",
    }
    
    for addr, desc in music_tables.items():
        print(f"   0x{addr:04X}: {desc}")
        # Show first few notes
        for i in range(0, min(12, len(data)-addr), 3):
            b1, b2, b3 = data[addr+i], data[addr+i+1], data[addr+i+2]
            if b1 != 0xFF:
                note = chr(b1) if 0x30 <= b1 <= 0x7F else f"0x{b1:02X}"
                print(f"      [{note:4s}] dur={b2:02X} cmd={b3:02X}")
    
    print("\n2. CODE REFERENCES TO MUSIC DATA:")
    print("-" * 80)
    
    # Find all MOV DPTR instructions pointing to music area
    music_refs = []
    for addr in range(0, 0x2000):
        if data[addr] == 0x90:  # MOV DPTR,#data16
            if addr + 2 < len(data):
                dptr = (data[addr+1] << 8) | data[addr+2]
                if 0x2700 <= dptr < 0x3300:  # Music data area
                    music_refs.append((addr, dptr))
    
    for code_addr, data_addr in music_refs[:10]:
        print(f"   Code 0x{code_addr:04X} → Data 0x{data_addr:04X}")
    
    print("\n3. COMMAND VALUE ANALYSIS:")
    print("-" * 80)
    
    # Analyze what commands lead to music data access
    print("   Looking for command values that trigger music code...")
    
    # Check code before each music reference
    for code_addr, data_addr in music_refs[:5]:
        print(f"\n   Code before 0x{code_addr:04X}:")
        # Go back 20 bytes and look for comparisons
        for i in range(max(0, code_addr-20), code_addr):
            if data[i] == 0xB4:  # CJNE A,#data,rel
                cmd_val = data[i+1] if i+1 < len(data) else 0
                print(f"      0x{i:04X}: Compare A with 0x{cmd_val:02X}")
            elif data[i] == 0xE5 and i+1 < len(data):  # MOV A,direct
                src = data[i+1]
                if src == 0xF0:  # Often temp storage for command
                    print(f"      0x{i:04X}: MOV A,0xF0 (load command)")
    
    print("\n4. MISSING COMMAND RANGE ANALYSIS:")
    print("-" * 80)
    
    known_cmds = [0xA0, 0xA2, 0xA3, 0xA4, 0xA6, 0xA7, 0xA8, 0xB0, 0xB5, 0xB6]
    print(f"   Known commands: {', '.join(f'0x{c:02X}' for c in known_cmds)}")
    print("\n   Gap analysis:")
    print("   - 0x00-0x5F: Likely note/data values")
    print("   - 0x60-0x9F: MISSING RANGE - likely music commands here!")
    print("   - 0xA0-0xA8: Direct control commands (found)")
    print("   - 0xA9-0xAF: MISSING RANGE")
    print("   - 0xB0: End marker")
    print("   - 0xB5-0xB6: Start markers")
    
    print("\n5. SUGGESTED TEST COMMANDS:")
    print("-" * 80)
    
    test_cmds = [
        ("Play music 0", [0xB5, 0x60, 0x00, 0xB0]),
        ("Play music 1", [0xB5, 0x60, 0x01, 0xB0]),
        ("Stop music", [0xB5, 0x61, 0xB0]),
        ("Alt music cmd", [0xB5, 0x65, 0x00, 0xB0]),
        ("Another variant", [0xB5, 0x68, 0x00, 0xB0]),
    ]
    
    print("   Test these command sequences:")
    for desc, cmd in test_cmds:
        hex_str = ' '.join(f'{b:02X}' for b in cmd)
        print(f"   {desc:20s}: {hex_str}")
    
    print("\n6. EXAMINING COMMAND DISPATCH MORE CAREFULLY:")
    print("-" * 80)
    
    # Look at the area around 0x00E0 where commands are dispatched
    print("   Command processing flow:")
    print("   - 0x00E0: Read buffer, check command type")
    print("   - 0x00F5: SUBB A,#0xA0 (check if >= 0xA0)")
    print("   - If < 0xA0: treated as data/note value")
    print("   - If >= 0xA0: dispatched to handler")
    print("\n   This means commands 0x60-0x9F are in the '<0xA0' path!")
    print("   Need to trace what happens to values in that range.")
    
    # Look for handling of values < 0xA0
    print("\n   Code at 0x00F9 (when A < 0xA0):")
    for i in range(0x00F9, 0x0110):
        print(f"      0x{i:04X}: {data[i]:02X}")
    
    return music_refs

def analyze_command_flow(data, start_addr):
    """Trace command flow from a specific address"""
    print(f"\n7. DETAILED FLOW ANALYSIS FROM 0x{start_addr:04X}:")
    print("-" * 80)
    
    opcodes_1byte = {
        0xA3: "INC DPTR",
        0x22: "RET",
        0xE0: "MOVX A,@DPTR",
        0xF0: "MOVX @DPTR,A",
        0x93: "MOVC A,@A+DPTR",
        0xC3: "CLR C",
    }
    
    opcodes_2byte = {
        0x74: "MOV A,#",
        0x75: "MOV direct,#",
        0x90: "MOV DPTR,#",
        0xE5: "MOV A,direct",
        0xF5: "MOV direct,A",
        0x94: "SUBB A,#",
        0xB4: "CJNE A,#",
        0x80: "SJMP",
    }
    
    addr = start_addr
    for _ in range(30):  # Disassemble 30 instructions
        if addr >= len(data):
            break
        
        opcode = data[addr]
        
        if opcode in opcodes_1byte:
            print(f"   0x{addr:04X}: {data[addr]:02X}       {opcodes_1byte[opcode]}")
            addr += 1
        elif opcode in opcodes_2byte:
            if addr + 1 < len(data):
                operand = data[addr+1]
                mnem = opcodes_2byte[opcode]
                if opcode == 0x90 and addr + 2 < len(data):
                    dptr = (data[addr+1] << 8) | data[addr+2]
                    print(f"   0x{addr:04X}: {data[addr]:02X} {data[addr+1]:02X} {data[addr+2]:02X} {mnem}0x{dptr:04X}")
                    addr += 3
                    continue
                print(f"   0x{addr:04X}: {data[addr]:02X} {operand:02X}    {mnem}0x{operand:02X}")
            addr += 2
        else:
            print(f"   0x{addr:04X}: {data[addr]:02X}")
            addr += 1

def main():
    filename = "/home/runner/work/Mephisto/Mephisto/sound_cpu_8051.bin"
    data = load_binary(filename)
    
    music_refs = find_music_commands(data)
    
    # Analyze the code flow for processing commands < 0xA0
    if music_refs:
        analyze_command_flow(data, 0x00F9)
    
    print("\n" + "=" * 80)
    print("CONCLUSION:")
    print("=" * 80)
    print("""
The firmware has TWO command systems:

1. Direct Commands (0xA0-0xA8):
   - Immediate control of AY-3-8910
   - Set frequency, amplitude directly
   
2. Music Commands (likely 0x60-0x9F):
   - Reference pre-stored music data
   - Play melodies, sequences
   - Use note tables for lookup

Commands 0x60-0x9F go through a different code path (< 0xA0 branch).
They likely index into the music data tables and trigger playback.

NEXT STEPS:
1. Test commands 0x60-0x70 with various parameters
2. Monitor what the firmware does at startup (might play intro music)
3. Analyze code at 0x00F9-0x0150 more carefully (< 0xA0 branch)
4. Use hardware/emulator to systematically test command values
""")

if __name__ == "__main__":
    main()
