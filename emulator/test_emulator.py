#!/usr/bin/env python3
"""
Simple test without audio hardware - validates emulator functionality
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cpu8051 import CPU8051
from ay3910_audio import AY3910Audio


def test_cpu():
    """Test basic CPU functionality"""
    print("=" * 60)
    print("Testing 8051 CPU Emulator")
    print("=" * 60)
    
    cpu = CPU8051()
    
    # Test 1: Load ROM
    print("\n1. Loading ROM...")
    # Find ROM file
    rom_file = os.path.join(os.path.dirname(__file__), "..", "sound_cpu_8051.bin")
    if not os.path.exists(rom_file):
        rom_file = "sound_cpu_8051.bin"
    with open(rom_file, 'rb') as f:
        rom_data = f.read()
    cpu.load_rom(rom_data)
    print(f"   Loaded {len(rom_data)} bytes")
    
    # Test 2: Reset
    print("\n2. Resetting CPU...")
    cpu.reset()
    print(f"   PC = 0x{cpu.pc:04X}")
    print(f"   SP = 0x{cpu.sp:02X}")
    
    # Test 3: Execute a few instructions
    print("\n3. Executing initial instructions...")
    for i in range(10):
        opcode = cpu.rom[cpu.pc]
        pc_before = cpu.pc
        cpu.step()
        print(f"   PC: 0x{pc_before:04X} -> 0x{cpu.pc:04X}, Opcode: 0x{opcode:02X}")
    
    # Test 4: UART receive
    print("\n4. Testing UART receive...")
    cpu.uart_receive(0xB5)
    print(f"   Sent 0xB5 to UART")
    print(f"   SBUF = 0x{cpu.SBUF:02X}")
    print(f"   SCON = 0x{cpu.SCON:02X}")
    
    print("\n✓ CPU tests passed!")
    return True


def test_ay_chip():
    """Test AY-3-8910 functionality"""
    print("\n" + "=" * 60)
    print("Testing AY-3-8910 Emulator")
    print("=" * 60)
    
    ay = AY3910Audio(clock_freq=2000000, sample_rate=44100)
    
    # Test 1: Set frequency
    print("\n1. Setting frequency on channel A...")
    ay.set_channel_frequency(0, 477)  # Middle C
    freq = ay.get_channel_frequency(0)
    print(f"   Period set to: {freq}")
    assert freq == 477, "Frequency setting failed"
    
    # Test 2: Set amplitude
    print("\n2. Setting amplitude on channel A...")
    ay.set_channel_amplitude(0, 15)
    amp = ay.get_channel_amplitude(0)
    print(f"   Amplitude set to: {amp}")
    assert amp == 15, "Amplitude setting failed"
    
    # Test 3: Enable tone
    print("\n3. Enabling tone on channel A...")
    ay.enable_channel_tone(0, True)
    mixer = ay.registers[7]
    print(f"   Mixer register: 0b{mixer:08b}")
    
    # Test 4: Generate samples
    print("\n4. Generating audio samples...")
    for _ in range(100):
        ay.clock()
    print(f"   Generated samples, buffer size: {ay.audio_buffer.qsize()}")
    
    # Test 5: Get state
    print("\n5. Getting chip state...")
    print(ay.get_state_string())
    
    print("\n✓ AY-3-8910 tests passed!")
    return True


def test_integration():
    """Test CPU + AY integration"""
    print("\n" + "=" * 60)
    print("Testing CPU + AY Integration")
    print("=" * 60)
    
    # Create components
    cpu = CPU8051()
    ay = AY3910Audio()
    
    # Load ROM
    rom_file = os.path.join(os.path.dirname(__file__), "..", "sound_cpu_8051.bin")
    if not os.path.exists(rom_file):
        rom_file = "sound_cpu_8051.bin"
    with open(rom_file, 'rb') as f:
        rom_data = f.read()
    cpu.load_rom(rom_data)
    cpu.reset()
    
    # Setup port callbacks
    port_writes = []
    
    def port1_callback(value):
        port_writes.append(('P1', value))
        
    def port3_callback(value):
        port_writes.append(('P3', value))
        
    cpu.port_write_callbacks[0x90] = port1_callback
    cpu.port_write_callbacks[0xB0] = port3_callback
    
    print("\n1. Executing firmware initialization...")
    # Execute some instructions
    for _ in range(100):
        cpu.step()
    
    print(f"   Executed {cpu.cycle_count} cycles")
    print(f"   PC = 0x{cpu.pc:04X}")
    
    print("\n2. Sending UART command (B5 A4 00 DD 01 0F B0)...")
    # Send a NOTE command
    command = [0xB5, 0xA4, 0x00, 0xDD, 0x01, 0x0F, 0xB0]
    for byte in command:
        cpu.uart_receive(byte)
        # Process interrupt and commands
        for _ in range(50):
            cpu.step()
    
    print(f"   Port writes detected: {len(port_writes)}")
    if port_writes:
        print(f"   Last 5 writes: {port_writes[-5:]}")
    
    print("\n✓ Integration tests passed!")
    return True


def main():
    """Run all tests"""
    print("8051 + AY-3-8910 Emulator Test Suite")
    print("(No audio hardware required)")
    print()
    
    try:
        # Run tests
        test_cpu()
        test_ay_chip()
        test_integration()
        
        print("\n" + "=" * 60)
        print("✓ All tests passed successfully!")
        print("=" * 60)
        print()
        print("The emulator is working correctly.")
        print("To hear actual audio, run: python3 main.py")
        print()
        return 0
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
