#!/usr/bin/env python3
"""
8051 Binary Analyzer and Disassembler
Reverse engineers the sound_cpu_8051.bin to understand UART command protocol
"""

import struct
import sys

# 8051 Instruction set - opcodes and mnemonics
OPCODES = {
    0x00: ("NOP", 1),
    0x01: ("AJMP addr11", 2),
    0x02: ("LJMP addr16", 3),
    0x03: ("RR A", 1),
    0x04: ("INC A", 1),
    0x05: ("INC direct", 2),
    0x06: ("INC @R0", 1),
    0x07: ("INC @R1", 1),
    0x08: ("INC R0", 1),
    0x09: ("INC R1", 1),
    0x0A: ("INC R2", 1),
    0x0B: ("INC R3", 1),
    0x0C: ("INC R4", 1),
    0x0D: ("INC R5", 1),
    0x0E: ("INC R6", 1),
    0x0F: ("INC R7", 1),
    0x10: ("JBC bit,rel", 3),
    0x11: ("ACALL addr11", 2),
    0x12: ("LCALL addr16", 3),
    0x13: ("RRC A", 1),
    0x14: ("DEC A", 1),
    0x15: ("DEC direct", 2),
    0x19: ("DEC R1", 1),
    0x1B: ("DEC R3", 1),
    0x20: ("JB bit,rel", 3),
    0x21: ("AJMP addr11", 2),
    0x22: ("RET", 1),
    0x24: ("ADD A,#data", 2),
    0x25: ("ADD A,direct", 2),
    0x30: ("JNB bit,rel", 3),
    0x32: ("RETI", 1),
    0x34: ("ADDC A,#data", 2),
    0x40: ("JC rel", 2),
    0x41: ("AJMP addr11", 2),
    0x42: ("ORL direct,A", 2),
    0x43: ("ORL direct,#data", 3),
    0x50: ("JNC rel", 2),
    0x53: ("ANL direct,#data", 3),
    0x54: ("ANL A,#data", 2),
    0x60: ("JZ rel", 2),
    0x61: ("AJMP addr11", 2),
    0x70: ("JNZ rel", 2),
    0x74: ("MOV A,#data", 2),
    0x75: ("MOV direct,#data", 3),
    0x78: ("MOV R0,#data", 2),
    0x79: ("MOV R1,#data", 2),
    0x7A: ("MOV R2,#data", 2),
    0x7B: ("MOV R3,#data", 2),
    0x7C: ("MOV R4,#data", 2),
    0x7D: ("MOV R5,#data", 2),
    0x7E: ("MOV R6,#data", 2),
    0x7F: ("MOV R7,#data", 2),
    0x80: ("SJMP rel", 2),
    0x81: ("AJMP addr11", 2),
    0x85: ("MOV direct,direct", 3),
    0x88: ("MOV direct,R0", 2),
    0x89: ("MOV direct,R1", 2),
    0x8A: ("MOV direct,R2", 2),
    0x8B: ("MOV direct,R3", 2),
    0x8C: ("MOV direct,R4", 2),
    0x8D: ("MOV direct,R5", 2),
    0x8E: ("MOV direct,R6", 2),
    0x8F: ("MOV direct,R7", 2),
    0x90: ("MOV DPTR,#data16", 3),
    0x92: ("MOV bit,C", 2),
    0x93: ("MOVC A,@A+DPTR", 1),
    0x94: ("SUBB A,#data", 2),
    0x95: ("SUBB A,direct", 2),
    0x9A: ("SUBB A,R2", 1),
    0xA2: ("MOV C,bit", 2),
    0xA3: ("INC DPTR", 1),
    0xA4: ("MUL AB", 1),
    0xA8: ("MOV R0,direct", 2),
    0xA9: ("MOV R1,direct", 2),
    0xAA: ("MOV R2,direct", 2),
    0xAB: ("MOV R3,direct", 2),
    0xB0: ("ANL C,/bit", 2),
    0xB4: ("CJNE A,#data,rel", 3),
    0xB5: ("CJNE A,direct,rel", 3),
    0xB8: ("CJNE R0,#data,rel", 3),
    0xB9: ("CJNE R1,#data,rel", 3),
    0xC0: ("PUSH direct", 2),
    0xC2: ("CLR bit", 2),
    0xC3: ("CLR C", 1),
    0xCA: ("XCH A,R2", 1),
    0xD0: ("POP direct", 2),
    0xD2: ("SETB bit", 2),
    0xD5: ("DJNZ direct,rel", 3),
    0xD8: ("DJNZ R0,rel", 2),
    0xD9: ("DJNZ R1,rel", 2),
    0xDA: ("DJNZ R2,rel", 2),
    0xDC: ("DJNZ R4,rel", 2),
    0xDD: ("DJNZ R5,rel", 2),
    0xE0: ("MOVX A,@DPTR", 1),
    0xE2: ("MOVX A,@R0", 1),
    0xE4: ("CLR A", 1),
    0xE5: ("MOV A,direct", 2),
    0xE6: ("MOV A,@R0", 1),
    0xE8: ("MOV A,R0", 1),
    0xE9: ("MOV A,R1", 1),
    0xEA: ("MOV A,R2", 1),
    0xEB: ("MOV A,R3", 1),
    0xEC: ("MOV A,R4", 1),
    0xED: ("MOV A,R5", 1),
    0xEE: ("MOV A,R6", 1),
    0xF0: ("MOVX @DPTR,A", 1),
    0xF2: ("MOVX @R0,A", 1),
    0xF4: ("CPL A", 1),
    0xF5: ("MOV direct,A", 2),
    0xF6: ("MOV @R0,A", 1),
    0xF8: ("MOV R0,A", 1),
    0xF9: ("MOV R1,A", 1),
    0xFB: ("MOV R3,A", 1),
    0xFC: ("MOV R4,A", 1),
    0xFD: ("MOV R5,A", 1),
    0xFE: ("MOV R6,A", 1),
    0xFF: ("MOV R7,A", 1),
}

# Important 8051 SFR addresses
SFR_NAMES = {
    0x80: "P0",     # Port 0
    0x81: "SP",     # Stack pointer
    0x87: "PCON",   # Power control
    0x88: "TCON",   # Timer control
    0x89: "TMOD",   # Timer mode
    0x8A: "TL0",    # Timer 0 low
    0x8B: "TL1",    # Timer 1 low
    0x8C: "TH0",    # Timer 0 high
    0x8D: "TH1",    # Timer 1 high
    0x90: "P1",     # Port 1 (AY-3-8910 bus!)
    0x98: "SCON",   # Serial control
    0x99: "SBUF",   # Serial buffer (UART!)
    0xA0: "P2",     # Port 2
    0xA8: "IE",     # Interrupt enable
    0xB0: "P3",     # Port 3
    0xB2: "REN",    # Receiver enable (part of SCON)
    0xB3: "TB8",    # Transmit bit 8 (part of SCON)
    0xB8: "IP",     # Interrupt priority
    0xD0: "PSW",    # Program status word
}

def load_binary(filename):
    """Load the binary file"""
    with open(filename, 'rb') as f:
        return bytearray(f.read())

def disassemble_instruction(data, addr):
    """Disassemble a single instruction"""
    if addr >= len(data):
        return None, 0
    
    opcode = data[addr]
    
    if opcode not in OPCODES:
        return f"DB 0x{opcode:02X}  ; Unknown opcode", 1
    
    mnem, length = OPCODES[opcode]
    
    # Build instruction string with operands
    instr = mnem
    operands = []
    
    for i in range(1, length):
        if addr + i < len(data):
            operands.append(data[addr + i])
    
    # Format the operands
    if length == 2:
        if "direct" in mnem:
            sfr = operands[0] if operands else 0
            sfr_name = SFR_NAMES.get(sfr, f"0x{sfr:02X}")
            instr = instr.replace("direct", sfr_name)
        elif "#data" in mnem:
            instr = instr.replace("#data", f"#0x{operands[0]:02X}")
        elif "rel" in mnem:
            rel = operands[0] if operands else 0
            if rel > 127:
                rel = rel - 256
            target = addr + length + rel
            instr = instr.replace("rel", f"0x{target:04X}")
    elif length == 3:
        if "addr16" in mnem:
            addr16 = (operands[0] << 8) | operands[1] if len(operands) >= 2 else 0
            instr = instr.replace("addr16", f"0x{addr16:04X}")
        elif "#data16" in mnem:
            data16 = (operands[0] << 8) | operands[1] if len(operands) >= 2 else 0
            instr = instr.replace("#data16", f"#0x{data16:04X}")
        elif "direct" in mnem and "#data" in mnem:
            sfr = operands[0] if operands else 0
            sfr_name = SFR_NAMES.get(sfr, f"0x{sfr:02X}")
            data_val = operands[1] if len(operands) >= 2 else 0
            instr = instr.replace("direct", sfr_name).replace("#data", f"#0x{data_val:02X}")
        elif "rel" in mnem:
            if "#data" in mnem:
                data_val = operands[0] if operands else 0
                rel = operands[1] if len(operands) >= 2 else 0
            else:
                sfr = operands[0] if operands else 0
                sfr_name = SFR_NAMES.get(sfr, f"0x{sfr:02X}")
                rel = operands[1] if len(operands) >= 2 else 0
                instr = instr.replace("direct", sfr_name)
                
            if rel > 127:
                rel = rel - 256
            target = addr + length + rel
            instr = instr.replace("rel", f"0x{target:04X}")
            if "#data" in instr:
                instr = instr.replace("#data", f"#0x{data_val:02X}")
    
    return instr, length

def analyze_interrupt_vectors(data):
    """Analyze interrupt vector table (first 0x2B bytes)"""
    print("\n=== INTERRUPT VECTOR TABLE ===")
    vectors = {
        0x0000: "RESET",
        0x0003: "EXT0 (External Interrupt 0)",
        0x000B: "TIMER0",
        0x0013: "EXT1 (External Interrupt 1)",
        0x001B: "TIMER1",
        0x0023: "UART (RI & TI)",
    }
    
    for addr, name in vectors.items():
        if addr < len(data):
            opcode = data[addr]
            if opcode == 0x02:  # LJMP
                target = (data[addr+1] << 8) | data[addr+2]
                print(f"{addr:04X}: {name:30s} -> LJMP 0x{target:04X}")
            else:
                print(f"{addr:04X}: {name:30s} -> 0x{opcode:02X}")

def find_uart_operations(data):
    """Find UART-related operations (SBUF accesses)"""
    print("\n=== UART OPERATIONS (SBUF 0x99 accesses) ===")
    uart_ops = []
    
    for addr in range(len(data) - 2):
        # Look for MOV operations with SBUF (0x99)
        if data[addr] == 0xF5 and data[addr+1] == 0x99:  # MOV 0x99,A
            uart_ops.append((addr, "UART_TX: MOV SBUF,A (transmit)"))
        elif data[addr] == 0xE5 and data[addr+1] == 0x99:  # MOV A,0x99
            uart_ops.append((addr, "UART_RX: MOV A,SBUF (receive)"))
        # Check for SBUF comparisons
        elif addr < len(data) - 3:
            if data[addr] == 0x90 and data[addr+1] == 0x00 and data[addr+2] == 0x99:  # MOV DPTR,#0x0099
                uart_ops.append((addr, "UART: Load DPTR with SBUF address"))
    
    for addr, desc in uart_ops[:20]:  # Show first 20
        print(f"{addr:04X}: {desc}")
    
    return uart_ops

def find_port_operations(data):
    """Find Port P1 operations (AY-3-8910 control)"""
    print("\n=== PORT P1 OPERATIONS (0x90 - AY-3-8910 bus) ===")
    port_ops = []
    
    for addr in range(len(data) - 2):
        # Look for P1 (0x90) operations
        if data[addr] == 0xF5 and data[addr+1] == 0x90:  # MOV P1,A
            port_ops.append((addr, "AY_WRITE: MOV P1,A (write to AY-3-8910)"))
        elif data[addr] == 0xE5 and data[addr+1] == 0x90:  # MOV A,P1
            port_ops.append((addr, "AY_READ: MOV A,P1 (read from AY-3-8910)"))
        elif data[addr] == 0x75 and data[addr+1] == 0x90:  # MOV P1,#data
            value = data[addr+2] if addr+2 < len(data) else 0
            port_ops.append((addr, f"AY_WRITE_IMM: MOV P1,#0x{value:02X}"))
    
    for addr, desc in port_ops[:30]:  # Show first 30
        print(f"{addr:04X}: {desc}")
    
    return port_ops

def disassemble_region(data, start, end, name):
    """Disassemble a region of code"""
    print(f"\n=== {name} ===")
    addr = start
    count = 0
    max_instructions = 50  # Limit output
    
    while addr < end and addr < len(data) and count < max_instructions:
        instr, length = disassemble_instruction(data, addr)
        if instr:
            # Get hex bytes
            hex_bytes = " ".join(f"{data[addr+i]:02X}" for i in range(min(length, end-addr)))
            print(f"{addr:04X}: {hex_bytes:12s} {instr}")
            addr += length
            count += 1
        else:
            break

def analyze_command_patterns(data):
    """Analyze potential command byte patterns"""
    print("\n=== COMMAND PATTERN ANALYSIS ===")
    
    # Look for byte comparisons that might be command codes
    commands = set()
    
    for addr in range(len(data) - 2):
        # CJNE A,#data,rel (0xB4)
        if data[addr] == 0xB4:
            cmd = data[addr+1]
            commands.add(cmd)
        # MOV A,#data followed by comparison context
        elif data[addr] == 0x74:
            cmd = data[addr+1]
            # Check if followed by comparison or jump
            if addr + 2 < len(data) and data[addr+2] in [0xB4, 0x60, 0x70]:
                commands.add(cmd)
    
    print(f"Found {len(commands)} potential command bytes:")
    for cmd in sorted(commands):
        if 0xA0 <= cmd <= 0xBF:  # Likely command range
            print(f"  0x{cmd:02X} ({cmd})")

def main():
    filename = "/home/runner/work/Mephisto/Mephisto/sound_cpu_8051.bin"
    print(f"Analyzing {filename}")
    
    data = load_binary(filename)
    print(f"Binary size: {len(data)} bytes (0x{len(data):04X})")
    
    # Analyze different aspects
    analyze_interrupt_vectors(data)
    uart_ops = find_uart_operations(data)
    port_ops = find_port_operations(data)
    analyze_command_patterns(data)
    
    # Disassemble key regions
    disassemble_region(data, 0x0000, 0x0030, "RESET and Initialization (0x0000-0x0030)")
    
    # Find UART interrupt handler (typically at 0x0023)
    if len(data) > 0x23:
        uart_vector = (data[0x24] << 8) | data[0x25] if data[0x23] == 0x02 else None
        if uart_vector:
            print(f"\nUART interrupt handler at: 0x{uart_vector:04X}")
            disassemble_region(data, uart_vector, uart_vector + 0x80, 
                             f"UART Interrupt Handler at 0x{uart_vector:04X}")
    
    # Disassemble around first UART operation
    if uart_ops:
        first_uart = uart_ops[0][0]
        print(f"\nFirst UART operation at: 0x{first_uart:04X}")
        disassemble_region(data, max(0, first_uart - 20), first_uart + 50,
                         f"Code around first UART op (0x{first_uart:04X})")

if __name__ == "__main__":
    main()
