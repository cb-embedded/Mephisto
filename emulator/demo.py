#!/usr/bin/env python3
"""
Demo script - plays a simple melody automatically

This script demonstrates the emulator by playing a melody without
requiring interactive input.
"""

import sys
import time
import threading
from cpu8051 import CPU8051
from ay3910_audio import AY3910Audio, AudioOutput


class AutomaticDemo:
    """Automated demo that plays music"""
    
    def __init__(self, rom_file, clock_freq=2000000, sample_rate=44100):
        """Initialize the demo system"""
        # Create components
        self.cpu = CPU8051()
        self.ay_chip = AY3910Audio(clock_freq, sample_rate)
        self.audio_output = AudioOutput(self.ay_chip, sample_rate)
        
        # Load ROM
        with open(rom_file, 'rb') as f:
            rom_data = f.read()
        self.cpu.load_rom(rom_data)
        
        # Setup port callbacks
        self.cpu.port_write_callbacks[0x90] = self.port1_write
        self.cpu.port_write_callbacks[0xB0] = self.port3_write
        
        # AY control state
        self.ay_data = 0
        self.ay_bc1 = 0
        self.ay_bc2 = 0
        self.ay_bdir = 0
        
        # Control
        self.running = False
        self.cpu_thread = None
        
    def port1_write(self, value):
        """Handle Port 1 writes"""
        self.ay_data = value
        self.update_ay_control()
        
    def port3_write(self, value):
        """Handle Port 3 writes"""
        self.ay_bc1 = (value >> 0) & 0x01
        self.ay_bdir = (value >> 4) & 0x01
        self.ay_bc2 = (value >> 5) & 0x01
        self.update_ay_control()
        
    def update_ay_control(self):
        """Update AY chip based on control signals"""
        if self.ay_bdir == 1 and self.ay_bc2 == 1 and self.ay_bc1 == 1:
            self.ay_chip.latch_address(self.ay_data)
        elif self.ay_bdir == 1 and self.ay_bc2 == 1 and self.ay_bc1 == 0:
            self.ay_chip.write_data(self.ay_data)
        elif self.ay_bdir == 0 and self.ay_bc2 == 1 and self.ay_bc1 == 1:
            self.cpu.P1 = self.ay_chip.read_data()
            
    def cpu_loop(self):
        """CPU execution loop"""
        cycles_per_audio_sample = int(self.ay_chip.clock_freq / self.ay_chip.sample_rate / 16)
        
        while self.running:
            for _ in range(cycles_per_audio_sample):
                if not self.running:
                    break
                self.cpu.step()
                
            for _ in range(16):
                self.ay_chip.clock()
                
    def send_command(self, command_bytes):
        """Send a UART command"""
        for byte in command_bytes:
            self.cpu.uart_receive(byte)
            
    def play_note(self, channel, freq_hz, amplitude, duration):
        """Play a note"""
        period = int(self.ay_chip.clock_freq / (16 * freq_hz))
        period_low = period & 0xFF
        period_high = (period >> 8) & 0x0F
        
        # Send NOTE command
        cmd = [0xB5, 0xA4, channel, period_low, period_high, amplitude, 0xB0]
        self.send_command(cmd)
        time.sleep(duration)
        
    def stop_all(self):
        """Stop all channels"""
        cmd = [0xB5, 0xA6, 0xB0]
        self.send_command(cmd)
        
    def run_demo(self):
        """Run the automated demo"""
        print("=" * 60)
        print("8051 + AY-3-8910 Emulator - Automated Demo")
        print("=" * 60)
        print()
        
        # Reset CPU
        self.cpu.reset()
        
        # Start audio
        self.audio_output.start()
        time.sleep(0.5)
        
        # Start CPU thread
        self.running = True
        self.cpu_thread = threading.Thread(target=self.cpu_loop, daemon=True)
        self.cpu_thread.start()
        
        print("System started!")
        print()
        
        # Give firmware time to initialize
        time.sleep(1)
        
        # Play a simple melody: C D E F G A B C
        notes = [
            ("C4", 262, 0.5),
            ("D4", 294, 0.5),
            ("E4", 330, 0.5),
            ("F4", 349, 0.5),
            ("G4", 392, 0.5),
            ("A4", 440, 0.5),
            ("B4", 494, 0.5),
            ("C5", 523, 1.0),
        ]
        
        print("Playing C major scale...")
        print()
        
        for name, freq, duration in notes:
            print(f"  Playing {name} ({freq} Hz) for {duration}s")
            self.play_note(0, freq, 12, duration)
            
        print()
        print("Playing C major chord...")
        # Play chord: C-E-G
        self.play_note(0, 262, 10, 0)  # C
        self.play_note(1, 330, 10, 0)  # E
        self.play_note(2, 392, 10, 2.0)  # G
        
        print()
        print("Stopping all channels...")
        self.stop_all()
        time.sleep(0.5)
        
        # Show final state
        print()
        print(self.ay_chip.get_state_string())
        
        # Cleanup
        print()
        print("Demo complete!")
        self.running = False
        self.audio_output.stop()


def main():
    """Main entry point"""
    import os
    
    # Find ROM file
    rom_file = "../sound_cpu_8051.bin"
    if not os.path.exists(rom_file):
        rom_file = "sound_cpu_8051.bin"
    if not os.path.exists(rom_file):
        print("Error: Cannot find sound_cpu_8051.bin")
        return 1
        
    print(f"Loading ROM: {rom_file}")
    print()
    
    # Create and run demo
    demo = AutomaticDemo(rom_file)
    
    try:
        demo.run_demo()
        return 0
    except KeyboardInterrupt:
        print("\nDemo interrupted by user")
        demo.running = False
        demo.audio_output.stop()
        return 0


if __name__ == "__main__":
    sys.exit(main())
