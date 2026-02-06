#!/usr/bin/env python3
"""
Main Emulator - Connects 8051 CPU to AY-3-8910 Sound Chip

This module ties together the 8051 CPU emulator and AY-3-8910 audio emulator,
providing UART input via stdin for real-time music playback.
"""

import sys
import threading
import time
import select
from cpu8051 import CPU8051
from ay3910_audio import AY3910Audio, AudioOutput


class SoundSystem:
    """Complete sound system emulator"""
    
    def __init__(self, rom_file, clock_freq=2000000, sample_rate=44100):
        """
        Initialize the sound system
        
        Args:
            rom_file: Path to 8051 binary file
            clock_freq: AY-3-8910 clock frequency
            sample_rate: Audio sample rate
        """
        # Create components
        self.cpu = CPU8051()
        self.ay_chip = AY3910Audio(clock_freq, sample_rate)
        self.audio_output = AudioOutput(self.ay_chip, sample_rate)
        
        # Load ROM
        with open(rom_file, 'rb') as f:
            rom_data = f.read()
        self.cpu.load_rom(rom_data)
        
        # Setup port callbacks for AY-3-8910 control
        self.cpu.port_write_callbacks[0x90] = self.port1_write
        self.cpu.port_write_callbacks[0xB0] = self.port3_write
        
        # AY-3-8910 control state
        self.ay_data = 0
        self.ay_bc1 = 0
        self.ay_bc2 = 0
        self.ay_bdir = 0
        
        # Control flags
        self.running = False
        self.cpu_thread = None
        self.stdin_thread = None
        
    def port1_write(self, value):
        """Handle Port 1 writes (data bus to AY-3-8910)"""
        self.ay_data = value
        self.update_ay_control()
        
    def port3_write(self, value):
        """Handle Port 3 writes (control signals to AY-3-8910)"""
        # P3.0 = BC1, P3.4 = BDIR, P3.5 = BC2
        self.ay_bc1 = (value >> 0) & 0x01
        self.ay_bdir = (value >> 4) & 0x01
        self.ay_bc2 = (value >> 5) & 0x01
        self.update_ay_control()
        
    def update_ay_control(self):
        """Update AY-3-8910 based on control signals"""
        # AY-3-8910 control modes:
        # BDIR BC2 BC1 | Function
        # ─────────────────────
        #  0   1   0   | Inactive
        #  0   1   1   | Read from PSG
        #  1   1   0   | Write to PSG
        #  1   1   1   | Latch address
        
        if self.ay_bdir == 1 and self.ay_bc2 == 1 and self.ay_bc1 == 1:
            # Latch address
            self.ay_chip.latch_address(self.ay_data)
        elif self.ay_bdir == 1 and self.ay_bc2 == 1 and self.ay_bc1 == 0:
            # Write data
            self.ay_chip.write_data(self.ay_data)
        elif self.ay_bdir == 0 and self.ay_bc2 == 1 and self.ay_bc1 == 1:
            # Read data (update P1)
            self.cpu.P1 = self.ay_chip.read_data()
            
    def cpu_loop(self):
        """Main CPU execution loop"""
        cycles_per_audio_sample = int(self.ay_chip.clock_freq / self.ay_chip.sample_rate / 16)
        
        while self.running:
            # Execute CPU cycles
            for _ in range(cycles_per_audio_sample):
                if not self.running:
                    break
                self.cpu.step()
                
            # Clock the AY chip to generate audio
            for _ in range(16):
                self.ay_chip.clock()
                
    def stdin_loop(self):
        """Read UART input from stdin"""
        print("UART input ready (stdin)")
        print("Paste hex bytes (e.g., B5 A4 00 DD 01 0F B0) or type 'q' to quit")
        print()
        
        while self.running:
            # Check if input is available (non-blocking)
            if sys.stdin in select.select([sys.stdin], [], [], 0.1)[0]:
                line = sys.stdin.readline().strip()
                
                if not line:
                    continue
                    
                # Check for quit command
                if line.lower() in ['q', 'quit', 'exit']:
                    print("Quitting...")
                    self.running = False
                    break
                    
                # Check for status command
                if line.lower() in ['s', 'status', 'state']:
                    print()
                    print(self.ay_chip.get_state_string())
                    print()
                    continue
                    
                # Parse hex bytes
                try:
                    # Remove any non-hex characters
                    hex_str = ''.join(c for c in line if c in '0123456789ABCDEFabcdef ')
                    bytes_data = bytes.fromhex(hex_str)
                    
                    # Send to UART
                    for byte in bytes_data:
                        self.cpu.uart_receive(byte)
                        
                    print(f"Sent {len(bytes_data)} bytes to UART")
                    
                except ValueError as e:
                    print(f"Error parsing hex: {e}")
                    print("Format: B5 A4 00 DD 01 0F B0")
                    
    def start(self):
        """Start the emulator"""
        print("=" * 60)
        print("8051 + AY-3-8910 Sound System Emulator")
        print("=" * 60)
        print()
        
        # Reset CPU
        self.cpu.reset()
        
        # Start audio output
        self.audio_output.start()
        time.sleep(0.5)  # Give audio time to start
        
        # Start threads
        self.running = True
        
        self.cpu_thread = threading.Thread(target=self.cpu_loop, daemon=True)
        self.cpu_thread.start()
        
        self.stdin_thread = threading.Thread(target=self.stdin_loop, daemon=True)
        self.stdin_thread.start()
        
        print("System started!")
        print()
        
        # Wait for threads
        try:
            while self.running:
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\nInterrupted by user")
            
        # Cleanup
        self.stop()
        
    def stop(self):
        """Stop the emulator"""
        print("Stopping system...")
        self.running = False
        
        if self.audio_output:
            self.audio_output.stop()
            
        print("System stopped")
        

def main():
    """Main entry point"""
    import os
    
    # Find the ROM file
    rom_file = "../sound_cpu_8051.bin"
    if not os.path.exists(rom_file):
        rom_file = "sound_cpu_8051.bin"
    if not os.path.exists(rom_file):
        print(f"Error: Cannot find sound_cpu_8051.bin")
        print("Please run from the emulator directory")
        return 1
        
    print(f"Loading ROM: {rom_file}")
    
    # Create and start system
    system = SoundSystem(rom_file, clock_freq=2000000, sample_rate=44100)
    system.start()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
