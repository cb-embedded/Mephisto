#!/usr/bin/env python3
"""
8051 CPU Emulator

A complete emulator for the 8051 microcontroller that can execute
the sound_cpu_8051.bin firmware.
"""

import struct


class CPU8051:
    """Complete 8051 CPU emulator"""
    
    def __init__(self):
        # Internal RAM (256 bytes: 128 bytes + 128 SFR)
        self.iram = bytearray(256)
        
        # External RAM (up to 64KB)
        self.xram = bytearray(65536)
        
        # ROM/Program memory (up to 64KB)
        self.rom = bytearray(65536)
        
        # CPU registers
        self.pc = 0x0000  # Program counter
        self.sp = 0x07    # Stack pointer (starts at 0x07)
        self.psw = 0x00   # Program Status Word
        self.acc = 0x00   # Accumulator
        self.b = 0x00     # B register
        self.dptr = 0x0000  # Data pointer (DPH:DPL)
        
        # Special Function Registers (SFR) - memory mapped at 0x80-0xFF
        self.P0 = 0xFF  # Port 0
        self.P1 = 0xFF  # Port 1
        self.P2 = 0xFF  # Port 2
        self.P3 = 0xFF  # Port 3
        self.TCON = 0x00  # Timer control
        self.TMOD = 0x00  # Timer mode
        self.TL0 = 0x00   # Timer 0 low
        self.TH0 = 0x00   # Timer 0 high
        self.TL1 = 0x00   # Timer 1 low
        self.TH1 = 0x00   # Timer 1 high
        self.SCON = 0x00  # Serial control
        self.SBUF = 0x00  # Serial buffer
        self.IE = 0x00    # Interrupt enable
        self.IP = 0x00    # Interrupt priority
        
        # Interrupt handling
        self.interrupt_pending = [False] * 6
        self.interrupt_enabled = False
        
        # Peripheral interfaces
        self.uart_rx_callback = None
        self.uart_tx_callback = None
        self.port_write_callbacks = {}
        
        # Execution state
        self.running = True
        self.cycle_count = 0
        
    def load_rom(self, data, offset=0):
        """Load binary data into ROM"""
        for i, byte in enumerate(data):
            self.rom[offset + i] = byte
            
    def reset(self):
        """Reset the CPU to initial state"""
        self.pc = 0x0000
        self.sp = 0x07
        self.psw = 0x00
        self.acc = 0x00
        self.b = 0x00
        self.dptr = 0x0000
        self.IE = 0x00
        self.running = True
        
    def read_sfr(self, addr):
        """Read Special Function Register"""
        if addr == 0x80:  # P0
            return self.P0
        elif addr == 0x81:  # SP
            return self.sp
        elif addr == 0x82:  # DPL
            return self.dptr & 0xFF
        elif addr == 0x83:  # DPH
            return (self.dptr >> 8) & 0xFF
        elif addr == 0x87:  # PCON
            return 0x00
        elif addr == 0x88:  # TCON
            return self.TCON
        elif addr == 0x89:  # TMOD
            return self.TMOD
        elif addr == 0x8A:  # TL0
            return self.TL0
        elif addr == 0x8B:  # TL1
            return self.TL1
        elif addr == 0x8C:  # TH0
            return self.TH0
        elif addr == 0x8D:  # TH1
            return self.TH1
        elif addr == 0x90:  # P1
            return self.P1
        elif addr == 0x98:  # SCON
            return self.SCON
        elif addr == 0x99:  # SBUF
            return self.SBUF
        elif addr == 0xA0:  # P2
            return self.P2
        elif addr == 0xA8:  # IE
            return self.IE
        elif addr == 0xB0:  # P3
            return self.P3
        elif addr == 0xB8:  # IP
            return self.IP
        elif addr == 0xD0:  # PSW
            return self.psw
        elif addr == 0xE0:  # ACC
            return self.acc
        elif addr == 0xF0:  # B
            return self.b
        else:
            return self.iram[addr]
            
    def write_sfr(self, addr, value):
        """Write Special Function Register"""
        value = value & 0xFF
        
        if addr == 0x80:  # P0
            self.P0 = value
        elif addr == 0x81:  # SP
            self.sp = value
        elif addr == 0x82:  # DPL
            self.dptr = (self.dptr & 0xFF00) | value
        elif addr == 0x83:  # DPH
            self.dptr = (self.dptr & 0x00FF) | (value << 8)
        elif addr == 0x88:  # TCON
            self.TCON = value
        elif addr == 0x89:  # TMOD
            self.TMOD = value
        elif addr == 0x8A:  # TL0
            self.TL0 = value
        elif addr == 0x8B:  # TL1
            self.TL1 = value
        elif addr == 0x8C:  # TH0
            self.TH0 = value
        elif addr == 0x8D:  # TH1
            self.TH1 = value
        elif addr == 0x90:  # P1
            self.P1 = value
            if 0x90 in self.port_write_callbacks:
                self.port_write_callbacks[0x90](value)
        elif addr == 0x98:  # SCON
            self.SCON = value
        elif addr == 0x99:  # SBUF
            self.SBUF = value
            if self.uart_tx_callback:
                self.uart_tx_callback(value)
        elif addr == 0xA0:  # P2
            self.P2 = value
        elif addr == 0xA8:  # IE
            self.IE = value
            self.interrupt_enabled = (value & 0x80) != 0
        elif addr == 0xB0:  # P3
            self.P3 = value
            if 0xB0 in self.port_write_callbacks:
                self.port_write_callbacks[0xB0](value)
        elif addr == 0xB8:  # IP
            self.IP = value
        elif addr == 0xD0:  # PSW
            self.psw = value
        elif addr == 0xE0:  # ACC
            self.acc = value
        elif addr == 0xF0:  # B
            self.b = value
        else:
            self.iram[addr] = value
            
    def read_direct(self, addr):
        """Read direct address (internal RAM or SFR)"""
        if addr >= 0x80:
            return self.read_sfr(addr)
        return self.iram[addr]
        
    def write_direct(self, addr, value):
        """Write direct address (internal RAM or SFR)"""
        if addr >= 0x80:
            self.write_sfr(addr, value)
        else:
            self.iram[addr] = value & 0xFF
            
    def fetch_byte(self):
        """Fetch next byte from program memory"""
        byte = self.rom[self.pc]
        self.pc = (self.pc + 1) & 0xFFFF
        return byte
        
    def fetch_word(self):
        """Fetch next word (16-bit) from program memory"""
        high = self.fetch_byte()
        low = self.fetch_byte()
        return (high << 8) | low
        
    def push(self, value):
        """Push byte onto stack"""
        self.sp = (self.sp + 1) & 0xFF
        self.write_direct(self.sp, value)
        
    def pop(self):
        """Pop byte from stack"""
        value = self.read_direct(self.sp)
        self.sp = (self.sp - 1) & 0xFF
        return value
        
    def uart_receive(self, byte):
        """Receive byte via UART"""
        self.SBUF = byte & 0xFF
        # Set RI (receive interrupt) flag in SCON
        self.SCON |= 0x01
        # Trigger UART interrupt if enabled
        if self.IE & 0x10:  # ES (serial interrupt enable)
            self.interrupt_pending[4] = True
            
    def execute_instruction(self):
        """Execute one instruction"""
        opcode = self.fetch_byte()
        
        # NOP
        if opcode == 0x00:
            self.cycle_count += 1
            
        # AJMP addr11
        elif (opcode & 0x1F) == 0x01:
            addr11 = ((opcode & 0xE0) << 3) | self.fetch_byte()
            self.pc = (self.pc & 0xF800) | addr11
            self.cycle_count += 2
            
        # LJMP addr16
        elif opcode == 0x02:
            addr = self.fetch_word()
            self.pc = addr
            self.cycle_count += 2
            
        # RR A
        elif opcode == 0x03:
            carry = self.acc & 0x01
            self.acc = ((self.acc >> 1) | (carry << 7)) & 0xFF
            self.cycle_count += 1
            
        # INC A
        elif opcode == 0x04:
            self.acc = (self.acc + 1) & 0xFF
            self.cycle_count += 1
            
        # INC direct
        elif opcode == 0x05:
            addr = self.fetch_byte()
            value = self.read_direct(addr)
            self.write_direct(addr, (value + 1) & 0xFF)
            self.cycle_count += 1
            
        # INC @R0 or INC @R1
        elif opcode in [0x06, 0x07]:
            r = opcode & 0x01
            addr = self.iram[r]
            value = self.iram[addr]
            self.iram[addr] = (value + 1) & 0xFF
            self.cycle_count += 1
            
        # INC R0-R7
        elif 0x08 <= opcode <= 0x0F:
            r = opcode & 0x07
            self.iram[r] = (self.iram[r] + 1) & 0xFF
            self.cycle_count += 1
            
        # JBC bit, rel
        elif opcode == 0x10:
            bit_addr = self.fetch_byte()
            rel = self.fetch_byte()
            # Read bit
            byte_addr = (bit_addr >> 3) | 0x20 if bit_addr < 0x80 else 0x80 + ((bit_addr >> 3) & 0x0F)
            bit_pos = bit_addr & 0x07
            byte_val = self.read_direct(byte_addr)
            if byte_val & (1 << bit_pos):
                # Clear bit
                self.write_direct(byte_addr, byte_val & ~(1 << bit_pos))
                # Jump
                if rel & 0x80:
                    self.pc = (self.pc - (256 - rel)) & 0xFFFF
                else:
                    self.pc = (self.pc + rel) & 0xFFFF
            self.cycle_count += 2
            
        # ACALL addr11
        elif (opcode & 0x1F) == 0x11:
            addr11 = ((opcode & 0xE0) << 3) | self.fetch_byte()
            self.push(self.pc & 0xFF)
            self.push((self.pc >> 8) & 0xFF)
            self.pc = (self.pc & 0xF800) | addr11
            self.cycle_count += 2
            
        # LCALL addr16
        elif opcode == 0x12:
            addr = self.fetch_word()
            self.push(self.pc & 0xFF)
            self.push((self.pc >> 8) & 0xFF)
            self.pc = addr
            self.cycle_count += 2
            
        # RRC A
        elif opcode == 0x13:
            carry = (self.psw >> 7) & 0x01
            new_carry = self.acc & 0x01
            self.acc = ((self.acc >> 1) | (carry << 7)) & 0xFF
            self.psw = (self.psw & 0x7F) | (new_carry << 7)
            self.cycle_count += 1
            
        # DEC A
        elif opcode == 0x14:
            self.acc = (self.acc - 1) & 0xFF
            self.cycle_count += 1
            
        # DEC direct
        elif opcode == 0x15:
            addr = self.fetch_byte()
            value = self.read_direct(addr)
            self.write_direct(addr, (value - 1) & 0xFF)
            self.cycle_count += 1
            
        # DEC @R0 or DEC @R1
        elif opcode in [0x16, 0x17]:
            r = opcode & 0x01
            addr = self.iram[r]
            value = self.iram[addr]
            self.iram[addr] = (value - 1) & 0xFF
            self.cycle_count += 1
            
        # DEC R0-R7
        elif 0x18 <= opcode <= 0x1F:
            r = opcode & 0x07
            self.iram[r] = (self.iram[r] - 1) & 0xFF
            self.cycle_count += 1
            
        # JB bit, rel
        elif opcode == 0x20:
            bit_addr = self.fetch_byte()
            rel = self.fetch_byte()
            # Read bit
            byte_addr = (bit_addr >> 3) | 0x20 if bit_addr < 0x80 else 0x80 + ((bit_addr >> 3) & 0x0F)
            bit_pos = bit_addr & 0x07
            byte_val = self.read_direct(byte_addr)
            if byte_val & (1 << bit_pos):
                if rel & 0x80:
                    self.pc = (self.pc - (256 - rel)) & 0xFFFF
                else:
                    self.pc = (self.pc + rel) & 0xFFFF
            self.cycle_count += 2
            
        # RET
        elif opcode == 0x22:
            high = self.pop()
            low = self.pop()
            self.pc = (high << 8) | low
            self.cycle_count += 2
            
        # RL A
        elif opcode == 0x23:
            carry = (self.acc >> 7) & 0x01
            self.acc = ((self.acc << 1) | carry) & 0xFF
            self.cycle_count += 1
            
        # ADD A, #data
        elif opcode == 0x24:
            data = self.fetch_byte()
            result = self.acc + data
            self.psw = (self.psw & 0x3F) | ((result >> 1) & 0x80) | ((result >> 8) & 0x80)
            self.acc = result & 0xFF
            self.cycle_count += 1
            
        # ADD A, direct
        elif opcode == 0x25:
            addr = self.fetch_byte()
            data = self.read_direct(addr)
            result = self.acc + data
            self.psw = (self.psw & 0x3F) | ((result >> 1) & 0x80) | ((result >> 8) & 0x80)
            self.acc = result & 0xFF
            self.cycle_count += 1
            
        # ADD A, @R0 or ADD A, @R1
        elif opcode in [0x26, 0x27]:
            r = opcode & 0x01
            addr = self.iram[r]
            data = self.iram[addr]
            result = self.acc + data
            self.psw = (self.psw & 0x3F) | ((result >> 1) & 0x80) | ((result >> 8) & 0x80)
            self.acc = result & 0xFF
            self.cycle_count += 1
            
        # ADD A, R0-R7
        elif 0x28 <= opcode <= 0x2F:
            r = opcode & 0x07
            result = self.acc + self.iram[r]
            self.psw = (self.psw & 0x3F) | ((result >> 1) & 0x80) | ((result >> 8) & 0x80)
            self.acc = result & 0xFF
            self.cycle_count += 1
            
        # JNB bit, rel
        elif opcode == 0x30:
            bit_addr = self.fetch_byte()
            rel = self.fetch_byte()
            # Read bit
            byte_addr = (bit_addr >> 3) | 0x20 if bit_addr < 0x80 else 0x80 + ((bit_addr >> 3) & 0x0F)
            bit_pos = bit_addr & 0x07
            byte_val = self.read_direct(byte_addr)
            if not (byte_val & (1 << bit_pos)):
                if rel & 0x80:
                    self.pc = (self.pc - (256 - rel)) & 0xFFFF
                else:
                    self.pc = (self.pc + rel) & 0xFFFF
            self.cycle_count += 2
            
        # RETI
        elif opcode == 0x32:
            high = self.pop()
            low = self.pop()
            self.pc = (high << 8) | low
            # Re-enable interrupts
            self.cycle_count += 2
            
        # RLC A
        elif opcode == 0x33:
            carry = (self.psw >> 7) & 0x01
            new_carry = (self.acc >> 7) & 0x01
            self.acc = ((self.acc << 1) | carry) & 0xFF
            self.psw = (self.psw & 0x7F) | (new_carry << 7)
            self.cycle_count += 1
            
        # ADDC A, #data
        elif opcode == 0x34:
            data = self.fetch_byte()
            carry = (self.psw >> 7) & 0x01
            result = self.acc + data + carry
            self.psw = (self.psw & 0x3F) | ((result >> 1) & 0x80) | ((result >> 8) & 0x80)
            self.acc = result & 0xFF
            self.cycle_count += 1
            
        # ADDC A, direct
        elif opcode == 0x35:
            addr = self.fetch_byte()
            data = self.read_direct(addr)
            carry = (self.psw >> 7) & 0x01
            result = self.acc + data + carry
            self.psw = (self.psw & 0x3F) | ((result >> 1) & 0x80) | ((result >> 8) & 0x80)
            self.acc = result & 0xFF
            self.cycle_count += 1
            
        # JC rel
        elif opcode == 0x40:
            rel = self.fetch_byte()
            if self.psw & 0x80:
                if rel & 0x80:
                    self.pc = (self.pc - (256 - rel)) & 0xFFFF
                else:
                    self.pc = (self.pc + rel) & 0xFFFF
            self.cycle_count += 2
            
        # ORL direct, A
        elif opcode == 0x42:
            addr = self.fetch_byte()
            value = self.read_direct(addr)
            self.write_direct(addr, value | self.acc)
            self.cycle_count += 1
            
        # ORL direct, #data
        elif opcode == 0x43:
            addr = self.fetch_byte()
            data = self.fetch_byte()
            value = self.read_direct(addr)
            self.write_direct(addr, value | data)
            self.cycle_count += 2
            
        # ORL A, #data
        elif opcode == 0x44:
            data = self.fetch_byte()
            self.acc |= data
            self.cycle_count += 1
            
        # ORL A, direct
        elif opcode == 0x45:
            addr = self.fetch_byte()
            self.acc |= self.read_direct(addr)
            self.cycle_count += 1
            
        # ORL A, @R0 or ORL A, @R1
        elif opcode in [0x46, 0x47]:
            r = opcode & 0x01
            addr = self.iram[r]
            self.acc |= self.iram[addr]
            self.cycle_count += 1
            
        # ORL A, R0-R7
        elif 0x48 <= opcode <= 0x4F:
            r = opcode & 0x07
            self.acc |= self.iram[r]
            self.cycle_count += 1
            
        # JNC rel
        elif opcode == 0x50:
            rel = self.fetch_byte()
            if not (self.psw & 0x80):
                if rel & 0x80:
                    self.pc = (self.pc - (256 - rel)) & 0xFFFF
                else:
                    self.pc = (self.pc + rel) & 0xFFFF
            self.cycle_count += 2
            
        # ANL direct, A
        elif opcode == 0x52:
            addr = self.fetch_byte()
            value = self.read_direct(addr)
            self.write_direct(addr, value & self.acc)
            self.cycle_count += 1
            
        # ANL direct, #data
        elif opcode == 0x53:
            addr = self.fetch_byte()
            data = self.fetch_byte()
            value = self.read_direct(addr)
            self.write_direct(addr, value & data)
            self.cycle_count += 2
            
        # ANL A, #data
        elif opcode == 0x54:
            data = self.fetch_byte()
            self.acc &= data
            self.cycle_count += 1
            
        # ANL A, direct
        elif opcode == 0x55:
            addr = self.fetch_byte()
            self.acc &= self.read_direct(addr)
            self.cycle_count += 1
            
        # ANL A, @R0 or ANL A, @R1
        elif opcode in [0x56, 0x57]:
            r = opcode & 0x01
            addr = self.iram[r]
            self.acc &= self.iram[addr]
            self.cycle_count += 1
            
        # ANL A, R0-R7
        elif 0x58 <= opcode <= 0x5F:
            r = opcode & 0x07
            self.acc &= self.iram[r]
            self.cycle_count += 1
            
        # JZ rel
        elif opcode == 0x60:
            rel = self.fetch_byte()
            if self.acc == 0:
                if rel & 0x80:
                    self.pc = (self.pc - (256 - rel)) & 0xFFFF
                else:
                    self.pc = (self.pc + rel) & 0xFFFF
            self.cycle_count += 2
            
        # XRL direct, A
        elif opcode == 0x62:
            addr = self.fetch_byte()
            value = self.read_direct(addr)
            self.write_direct(addr, value ^ self.acc)
            self.cycle_count += 1
            
        # XRL direct, #data
        elif opcode == 0x63:
            addr = self.fetch_byte()
            data = self.fetch_byte()
            value = self.read_direct(addr)
            self.write_direct(addr, value ^ data)
            self.cycle_count += 2
            
        # XRL A, #data
        elif opcode == 0x64:
            data = self.fetch_byte()
            self.acc ^= data
            self.cycle_count += 1
            
        # XRL A, direct
        elif opcode == 0x65:
            addr = self.fetch_byte()
            self.acc ^= self.read_direct(addr)
            self.cycle_count += 1
            
        # XRL A, @R0 or XRL A, @R1
        elif opcode in [0x66, 0x67]:
            r = opcode & 0x01
            addr = self.iram[r]
            self.acc ^= self.iram[addr]
            self.cycle_count += 1
            
        # XRL A, R0-R7
        elif 0x68 <= opcode <= 0x6F:
            r = opcode & 0x07
            self.acc ^= self.iram[r]
            self.cycle_count += 1
            
        # JNZ rel
        elif opcode == 0x70:
            rel = self.fetch_byte()
            if self.acc != 0:
                if rel & 0x80:
                    self.pc = (self.pc - (256 - rel)) & 0xFFFF
                else:
                    self.pc = (self.pc + rel) & 0xFFFF
            self.cycle_count += 2
            
        # ORL C, bit
        elif opcode == 0x72:
            bit_addr = self.fetch_byte()
            # Read bit
            byte_addr = (bit_addr >> 3) | 0x20 if bit_addr < 0x80 else 0x80 + ((bit_addr >> 3) & 0x0F)
            bit_pos = bit_addr & 0x07
            byte_val = self.read_direct(byte_addr)
            bit_val = (byte_val >> bit_pos) & 0x01
            carry = (self.psw >> 7) & 0x01
            self.psw = (self.psw & 0x7F) | ((carry | bit_val) << 7)
            self.cycle_count += 2
            
        # JMP @A+DPTR
        elif opcode == 0x73:
            self.pc = (self.dptr + self.acc) & 0xFFFF
            self.cycle_count += 2
            
        # MOV A, #data
        elif opcode == 0x74:
            self.acc = self.fetch_byte()
            self.cycle_count += 1
            
        # MOV direct, #data
        elif opcode == 0x75:
            addr = self.fetch_byte()
            data = self.fetch_byte()
            self.write_direct(addr, data)
            self.cycle_count += 2
            
        # MOV @R0, #data or MOV @R1, #data
        elif opcode in [0x76, 0x77]:
            r = opcode & 0x01
            data = self.fetch_byte()
            addr = self.iram[r]
            self.iram[addr] = data
            self.cycle_count += 1
            
        # MOV R0-R7, #data
        elif 0x78 <= opcode <= 0x7F:
            r = opcode & 0x07
            self.iram[r] = self.fetch_byte()
            self.cycle_count += 1
            
        # SJMP rel
        elif opcode == 0x80:
            rel = self.fetch_byte()
            if rel & 0x80:
                self.pc = (self.pc - (256 - rel)) & 0xFFFF
            else:
                self.pc = (self.pc + rel) & 0xFFFF
            self.cycle_count += 2
            
        # ANL C, bit
        elif opcode == 0x82:
            bit_addr = self.fetch_byte()
            # Read bit
            byte_addr = (bit_addr >> 3) | 0x20 if bit_addr < 0x80 else 0x80 + ((bit_addr >> 3) & 0x0F)
            bit_pos = bit_addr & 0x07
            byte_val = self.read_direct(byte_addr)
            bit_val = (byte_val >> bit_pos) & 0x01
            carry = (self.psw >> 7) & 0x01
            self.psw = (self.psw & 0x7F) | ((carry & bit_val) << 7)
            self.cycle_count += 2
            
        # MOVC A, @A+PC
        elif opcode == 0x83:
            addr = (self.pc + self.acc) & 0xFFFF
            self.acc = self.rom[addr]
            self.cycle_count += 2
            
        # DIV AB
        elif opcode == 0x84:
            if self.b == 0:
                # Overflow
                self.psw |= 0x04
            else:
                quotient = self.acc // self.b
                remainder = self.acc % self.b
                self.acc = quotient
                self.b = remainder
                self.psw &= 0xFB  # Clear OV
            self.psw &= 0x7F  # Clear C
            self.cycle_count += 4
            
        # MOV direct, direct
        elif opcode == 0x85:
            src = self.fetch_byte()
            dst = self.fetch_byte()
            self.write_direct(dst, self.read_direct(src))
            self.cycle_count += 2
            
        # MOV direct, @R0 or MOV direct, @R1
        elif opcode in [0x86, 0x87]:
            r = opcode & 0x01
            dst = self.fetch_byte()
            addr = self.iram[r]
            self.write_direct(dst, self.iram[addr])
            self.cycle_count += 2
            
        # MOV direct, R0-R7
        elif 0x88 <= opcode <= 0x8F:
            r = opcode & 0x07
            dst = self.fetch_byte()
            self.write_direct(dst, self.iram[r])
            self.cycle_count += 2
            
        # MOV DPTR, #data16
        elif opcode == 0x90:
            self.dptr = self.fetch_word()
            self.cycle_count += 2
            
        # MOV bit, C
        elif opcode == 0x92:
            bit_addr = self.fetch_byte()
            carry = (self.psw >> 7) & 0x01
            # Write bit
            byte_addr = (bit_addr >> 3) | 0x20 if bit_addr < 0x80 else 0x80 + ((bit_addr >> 3) & 0x0F)
            bit_pos = bit_addr & 0x07
            byte_val = self.read_direct(byte_addr)
            if carry:
                byte_val |= (1 << bit_pos)
            else:
                byte_val &= ~(1 << bit_pos)
            self.write_direct(byte_addr, byte_val)
            self.cycle_count += 2
            
        # MOVC A, @A+DPTR
        elif opcode == 0x93:
            addr = (self.dptr + self.acc) & 0xFFFF
            self.acc = self.rom[addr]
            self.cycle_count += 2
            
        # SUBB A, #data
        elif opcode == 0x94:
            data = self.fetch_byte()
            carry = (self.psw >> 7) & 0x01
            result = self.acc - data - carry
            self.psw = (self.psw & 0x3F) | ((result >> 1) & 0x80) | ((result >> 8) & 0x80)
            self.acc = result & 0xFF
            self.cycle_count += 1
            
        # SUBB A, direct
        elif opcode == 0x95:
            addr = self.fetch_byte()
            data = self.read_direct(addr)
            carry = (self.psw >> 7) & 0x01
            result = self.acc - data - carry
            self.psw = (self.psw & 0x3F) | ((result >> 1) & 0x80) | ((result >> 8) & 0x80)
            self.acc = result & 0xFF
            self.cycle_count += 1
            
        # SUBB A, @R0 or SUBB A, @R1
        elif opcode in [0x96, 0x97]:
            r = opcode & 0x01
            addr = self.iram[r]
            data = self.iram[addr]
            carry = (self.psw >> 7) & 0x01
            result = self.acc - data - carry
            self.psw = (self.psw & 0x3F) | ((result >> 1) & 0x80) | ((result >> 8) & 0x80)
            self.acc = result & 0xFF
            self.cycle_count += 1
            
        # SUBB A, R0-R7
        elif 0x98 <= opcode <= 0x9F:
            r = opcode & 0x07
            carry = (self.psw >> 7) & 0x01
            result = self.acc - self.iram[r] - carry
            self.psw = (self.psw & 0x3F) | ((result >> 1) & 0x80) | ((result >> 8) & 0x80)
            self.acc = result & 0xFF
            self.cycle_count += 1
            
        # ORL C, /bit
        elif opcode == 0xA0:
            bit_addr = self.fetch_byte()
            # Read bit
            byte_addr = (bit_addr >> 3) | 0x20 if bit_addr < 0x80 else 0x80 + ((bit_addr >> 3) & 0x0F)
            bit_pos = bit_addr & 0x07
            byte_val = self.read_direct(byte_addr)
            bit_val = ((byte_val >> bit_pos) & 0x01) ^ 1  # Complement
            carry = (self.psw >> 7) & 0x01
            self.psw = (self.psw & 0x7F) | ((carry | bit_val) << 7)
            self.cycle_count += 2
            
        # MOV C, bit
        elif opcode == 0xA2:
            bit_addr = self.fetch_byte()
            # Read bit
            byte_addr = (bit_addr >> 3) | 0x20 if bit_addr < 0x80 else 0x80 + ((bit_addr >> 3) & 0x0F)
            bit_pos = bit_addr & 0x07
            byte_val = self.read_direct(byte_addr)
            bit_val = (byte_val >> bit_pos) & 0x01
            self.psw = (self.psw & 0x7F) | (bit_val << 7)
            self.cycle_count += 1
            
        # INC DPTR
        elif opcode == 0xA3:
            self.dptr = (self.dptr + 1) & 0xFFFF
            self.cycle_count += 2
            
        # MUL AB
        elif opcode == 0xA4:
            result = self.acc * self.b
            self.acc = result & 0xFF
            self.b = (result >> 8) & 0xFF
            if result > 255:
                self.psw |= 0x04  # Set OV
            else:
                self.psw &= 0xFB  # Clear OV
            self.psw &= 0x7F  # Clear C
            self.cycle_count += 4
            
        # MOV @R0, direct or MOV @R1, direct
        elif opcode in [0xA6, 0xA7]:
            r = opcode & 0x01
            src = self.fetch_byte()
            addr = self.iram[r]
            self.iram[addr] = self.read_direct(src)
            self.cycle_count += 2
            
        # MOV R0-R7, direct
        elif 0xA8 <= opcode <= 0xAF:
            r = opcode & 0x07
            src = self.fetch_byte()
            self.iram[r] = self.read_direct(src)
            self.cycle_count += 2
            
        # ANL C, /bit
        elif opcode == 0xB0:
            bit_addr = self.fetch_byte()
            # Read bit
            byte_addr = (bit_addr >> 3) | 0x20 if bit_addr < 0x80 else 0x80 + ((bit_addr >> 3) & 0x0F)
            bit_pos = bit_addr & 0x07
            byte_val = self.read_direct(byte_addr)
            bit_val = ((byte_val >> bit_pos) & 0x01) ^ 1  # Complement
            carry = (self.psw >> 7) & 0x01
            self.psw = (self.psw & 0x7F) | ((carry & bit_val) << 7)
            self.cycle_count += 2
            
        # CPL bit
        elif opcode == 0xB2:
            bit_addr = self.fetch_byte()
            # Toggle bit
            byte_addr = (bit_addr >> 3) | 0x20 if bit_addr < 0x80 else 0x80 + ((bit_addr >> 3) & 0x0F)
            bit_pos = bit_addr & 0x07
            byte_val = self.read_direct(byte_addr)
            byte_val ^= (1 << bit_pos)
            self.write_direct(byte_addr, byte_val)
            self.cycle_count += 1
            
        # CPL C
        elif opcode == 0xB3:
            self.psw ^= 0x80
            self.cycle_count += 1
            
        # CJNE A, #data, rel
        elif opcode == 0xB4:
            data = self.fetch_byte()
            rel = self.fetch_byte()
            if self.acc != data:
                if rel & 0x80:
                    self.pc = (self.pc - (256 - rel)) & 0xFFFF
                else:
                    self.pc = (self.pc + rel) & 0xFFFF
            if self.acc < data:
                self.psw |= 0x80
            else:
                self.psw &= 0x7F
            self.cycle_count += 2
            
        # CJNE A, direct, rel
        elif opcode == 0xB5:
            addr = self.fetch_byte()
            data = self.read_direct(addr)
            rel = self.fetch_byte()
            if self.acc != data:
                if rel & 0x80:
                    self.pc = (self.pc - (256 - rel)) & 0xFFFF
                else:
                    self.pc = (self.pc + rel) & 0xFFFF
            if self.acc < data:
                self.psw |= 0x80
            else:
                self.psw &= 0x7F
            self.cycle_count += 2
            
        # CJNE @R0, #data, rel or CJNE @R1, #data, rel
        elif opcode in [0xB6, 0xB7]:
            r = opcode & 0x01
            data = self.fetch_byte()
            rel = self.fetch_byte()
            addr = self.iram[r]
            value = self.iram[addr]
            if value != data:
                if rel & 0x80:
                    self.pc = (self.pc - (256 - rel)) & 0xFFFF
                else:
                    self.pc = (self.pc + rel) & 0xFFFF
            if value < data:
                self.psw |= 0x80
            else:
                self.psw &= 0x7F
            self.cycle_count += 2
            
        # CJNE R0-R7, #data, rel
        elif 0xB8 <= opcode <= 0xBF:
            r = opcode & 0x07
            data = self.fetch_byte()
            rel = self.fetch_byte()
            value = self.iram[r]
            if value != data:
                if rel & 0x80:
                    self.pc = (self.pc - (256 - rel)) & 0xFFFF
                else:
                    self.pc = (self.pc + rel) & 0xFFFF
            if value < data:
                self.psw |= 0x80
            else:
                self.psw &= 0x7F
            self.cycle_count += 2
            
        # PUSH direct
        elif opcode == 0xC0:
            addr = self.fetch_byte()
            self.push(self.read_direct(addr))
            self.cycle_count += 2
            
        # CLR bit
        elif opcode == 0xC2:
            bit_addr = self.fetch_byte()
            # Clear bit
            byte_addr = (bit_addr >> 3) | 0x20 if bit_addr < 0x80 else 0x80 + ((bit_addr >> 3) & 0x0F)
            bit_pos = bit_addr & 0x07
            byte_val = self.read_direct(byte_addr)
            self.write_direct(byte_addr, byte_val & ~(1 << bit_pos))
            self.cycle_count += 1
            
        # CLR C
        elif opcode == 0xC3:
            self.psw &= 0x7F
            self.cycle_count += 1
            
        # SWAP A
        elif opcode == 0xC4:
            self.acc = ((self.acc & 0x0F) << 4) | ((self.acc & 0xF0) >> 4)
            self.cycle_count += 1
            
        # XCH A, direct
        elif opcode == 0xC5:
            addr = self.fetch_byte()
            temp = self.acc
            self.acc = self.read_direct(addr)
            self.write_direct(addr, temp)
            self.cycle_count += 1
            
        # XCH A, @R0 or XCH A, @R1
        elif opcode in [0xC6, 0xC7]:
            r = opcode & 0x01
            addr = self.iram[r]
            temp = self.acc
            self.acc = self.iram[addr]
            self.iram[addr] = temp
            self.cycle_count += 1
            
        # XCH A, R0-R7
        elif 0xC8 <= opcode <= 0xCF:
            r = opcode & 0x07
            temp = self.acc
            self.acc = self.iram[r]
            self.iram[r] = temp
            self.cycle_count += 1
            
        # POP direct
        elif opcode == 0xD0:
            addr = self.fetch_byte()
            self.write_direct(addr, self.pop())
            self.cycle_count += 2
            
        # SETB bit
        elif opcode == 0xD2:
            bit_addr = self.fetch_byte()
            # Set bit
            byte_addr = (bit_addr >> 3) | 0x20 if bit_addr < 0x80 else 0x80 + ((bit_addr >> 3) & 0x0F)
            bit_pos = bit_addr & 0x07
            byte_val = self.read_direct(byte_addr)
            self.write_direct(byte_addr, byte_val | (1 << bit_pos))
            self.cycle_count += 1
            
        # SETB C
        elif opcode == 0xD3:
            self.psw |= 0x80
            self.cycle_count += 1
            
        # DA A
        elif opcode == 0xD4:
            lower = self.acc & 0x0F
            upper = (self.acc >> 4) & 0x0F
            carry = (self.psw >> 7) & 0x01
            
            if lower > 9 or (self.psw & 0x40):
                self.acc = (self.acc + 6) & 0xFF
                
            if upper > 9 or carry:
                self.acc = (self.acc + 0x60) & 0xFF
                self.psw |= 0x80
            self.cycle_count += 1
            
        # DJNZ direct, rel
        elif opcode == 0xD5:
            addr = self.fetch_byte()
            rel = self.fetch_byte()
            value = (self.read_direct(addr) - 1) & 0xFF
            self.write_direct(addr, value)
            if value != 0:
                if rel & 0x80:
                    self.pc = (self.pc - (256 - rel)) & 0xFFFF
                else:
                    self.pc = (self.pc + rel) & 0xFFFF
            self.cycle_count += 2
            
        # XCHD A, @R0 or XCHD A, @R1
        elif opcode in [0xD6, 0xD7]:
            r = opcode & 0x01
            addr = self.iram[r]
            temp = self.acc & 0x0F
            self.acc = (self.acc & 0xF0) | (self.iram[addr] & 0x0F)
            self.iram[addr] = (self.iram[addr] & 0xF0) | temp
            self.cycle_count += 1
            
        # DJNZ R0-R7, rel
        elif 0xD8 <= opcode <= 0xDF:
            r = opcode & 0x07
            rel = self.fetch_byte()
            self.iram[r] = (self.iram[r] - 1) & 0xFF
            if self.iram[r] != 0:
                if rel & 0x80:
                    self.pc = (self.pc - (256 - rel)) & 0xFFFF
                else:
                    self.pc = (self.pc + rel) & 0xFFFF
            self.cycle_count += 2
            
        # MOVX A, @DPTR
        elif opcode == 0xE0:
            self.acc = self.xram[self.dptr]
            self.cycle_count += 2
            
        # MOVX A, @R0 or MOVX A, @R1
        elif opcode in [0xE2, 0xE3]:
            r = opcode & 0x01
            addr = self.iram[r]
            self.acc = self.xram[addr]
            self.cycle_count += 2
            
        # CLR A
        elif opcode == 0xE4:
            self.acc = 0
            self.cycle_count += 1
            
        # MOV A, direct
        elif opcode == 0xE5:
            addr = self.fetch_byte()
            self.acc = self.read_direct(addr)
            self.cycle_count += 1
            
        # MOV A, @R0 or MOV A, @R1
        elif opcode in [0xE6, 0xE7]:
            r = opcode & 0x01
            addr = self.iram[r]
            self.acc = self.iram[addr]
            self.cycle_count += 1
            
        # MOV A, R0-R7
        elif 0xE8 <= opcode <= 0xEF:
            r = opcode & 0x07
            self.acc = self.iram[r]
            self.cycle_count += 1
            
        # MOVX @DPTR, A
        elif opcode == 0xF0:
            self.xram[self.dptr] = self.acc
            self.cycle_count += 2
            
        # MOVX @R0, A or MOVX @R1, A
        elif opcode in [0xF2, 0xF3]:
            r = opcode & 0x01
            addr = self.iram[r]
            self.xram[addr] = self.acc
            self.cycle_count += 2
            
        # CPL A
        elif opcode == 0xF4:
            self.acc = self.acc ^ 0xFF
            self.cycle_count += 1
            
        # MOV direct, A
        elif opcode == 0xF5:
            addr = self.fetch_byte()
            self.write_direct(addr, self.acc)
            self.cycle_count += 1
            
        # MOV @R0, A or MOV @R1, A
        elif opcode in [0xF6, 0xF7]:
            r = opcode & 0x01
            addr = self.iram[r]
            self.iram[addr] = self.acc
            self.cycle_count += 1
            
        # MOV R0-R7, A
        elif 0xF8 <= opcode <= 0xFF:
            r = opcode & 0x07
            self.iram[r] = self.acc
            self.cycle_count += 1
            
        else:
            print(f"Unimplemented opcode: 0x{opcode:02X} at PC=0x{self.pc-1:04X}")
            self.running = False
            
    def step(self):
        """Execute one instruction and handle interrupts"""
        # Check for interrupts
        if self.interrupt_enabled:
            # Priority: EXT0 > TIMER0 > EXT1 > TIMER1 > SERIAL
            # For this firmware, we mainly care about UART (serial) interrupt
            if self.interrupt_pending[4] and (self.IE & 0x10):  # Serial interrupt
                self.interrupt_pending[4] = False
                # Call interrupt handler at 0x0023
                self.push(self.pc & 0xFF)
                self.push((self.pc >> 8) & 0xFF)
                self.pc = 0x0023
                
        # Execute one instruction
        self.execute_instruction()
        
    def run(self, max_cycles=None):
        """Run the CPU"""
        start_cycle = self.cycle_count
        while self.running:
            self.step()
            if max_cycles and (self.cycle_count - start_cycle) >= max_cycles:
                break
