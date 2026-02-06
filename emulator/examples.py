#!/usr/bin/env python3
"""
Example: Using the emulator programmatically

This shows how to use the emulator components in your own code.
"""

import time
from cpu8051 import CPU8051
from ay3910_audio import AY3910Audio, AudioOutput


def example_1_simple_tone():
    """Example 1: Play a simple tone without CPU"""
    print("Example 1: Playing a simple tone (no CPU)")
    print("-" * 60)
    
    # Create AY chip and audio output
    ay = AY3910Audio(clock_freq=2000000, sample_rate=44100)
    audio = AudioOutput(ay, sample_rate=44100)
    
    # Start audio
    audio.start()
    if not audio.is_running():
        print("Warning: Audio not available, continuing without sound")
    
    # Set up a 440 Hz tone on channel A
    period = ay.frequency_to_period(440)  # A440
    ay.set_channel_frequency(0, period)
    ay.set_channel_amplitude(0, 15)  # Max volume
    ay.enable_channel_tone(0, True)
    
    print(f"Playing A440 for 2 seconds...")
    print(ay.get_state_string())
    
    # Generate audio for 2 seconds
    for _ in range(44100 * 2 // 16):
        for _ in range(16):
            ay.clock()
    
    time.sleep(2)
    
    # Stop
    ay.set_channel_amplitude(0, 0)
    time.sleep(0.5)
    audio.stop()
    
    print("Done!\n")


def example_2_chord():
    """Example 2: Play a chord"""
    print("Example 2: Playing a C major chord")
    print("-" * 60)
    
    # Create AY chip and audio output
    ay = AY3910Audio(clock_freq=2000000, sample_rate=44100)
    audio = AudioOutput(ay, sample_rate=44100)
    
    # Start audio
    audio.start()
    if not audio.is_running():
        print("Warning: Audio not available, continuing without sound")
    
    # Set up C major chord (C-E-G)
    notes = [
        (0, 262, "C"),  # Channel A
        (1, 330, "E"),  # Channel B
        (2, 392, "G"),  # Channel C
    ]
    
    for channel, freq, name in notes:
        period = ay.frequency_to_period(freq)
        ay.set_channel_frequency(channel, period)
        ay.set_channel_amplitude(channel, 10)
        ay.enable_channel_tone(channel, True)
        print(f"Channel {chr(ord('A')+channel)}: {name} ({freq} Hz)")
    
    print("\nPlaying chord for 2 seconds...")
    
    # Generate audio for 2 seconds
    for _ in range(44100 * 2 // 16):
        for _ in range(16):
            ay.clock()
    
    time.sleep(2)
    
    # Stop
    for channel in range(3):
        ay.set_channel_amplitude(channel, 0)
    
    time.sleep(0.5)
    audio.stop()
    
    print("Done!\n")


def example_3_with_cpu():
    """Example 3: Using the CPU to control the sound chip"""
    print("Example 3: Using CPU to send UART commands")
    print("-" * 60)
    
    import threading
    
    # Create components
    cpu = CPU8051()
    ay = AY3910Audio(clock_freq=2000000, sample_rate=44100)
    audio = AudioOutput(ay, sample_rate=44100)
    
    # Load ROM
    rom_file = os.path.join(os.path.dirname(__file__), "..", "sound_cpu_8051.bin")
    if not os.path.exists(rom_file):
        rom_file = "sound_cpu_8051.bin"
    with open(rom_file, 'rb') as f:
        rom_data = f.read()
    cpu.load_rom(rom_data)
    cpu.reset()
    
    # Setup port callbacks
    ay_data = [0]
    ay_control = {'bc1': 0, 'bc2': 0, 'bdir': 0}
    
    def port1_write(value):
        ay_data[0] = value
        update_ay()
        
    def port3_write(value):
        ay_control['bc1'] = (value >> 0) & 0x01
        ay_control['bdir'] = (value >> 4) & 0x01
        ay_control['bc2'] = (value >> 5) & 0x01
        update_ay()
        
    def update_ay():
        bdir, bc2, bc1 = ay_control['bdir'], ay_control['bc2'], ay_control['bc1']
        if bdir == 1 and bc2 == 1 and bc1 == 1:
            ay.latch_address(ay_data[0])
        elif bdir == 1 and bc2 == 1 and bc1 == 0:
            ay.write_data(ay_data[0])
    
    cpu.port_write_callbacks[0x90] = port1_write
    cpu.port_write_callbacks[0xB0] = port3_write
    
    # Start audio
    audio.start()
    if not audio.is_running():
        print("Warning: Audio not available, continuing without sound")
    
    # Start CPU thread
    running = [True]
    
    def cpu_loop():
        cycles_per_sample = int(2000000 / 44100 / 16)
        while running[0]:
            for _ in range(cycles_per_sample):
                cpu.step()
            for _ in range(16):
                ay.clock()
    
    thread = threading.Thread(target=cpu_loop, daemon=True)
    thread.start()
    
    # Wait for initialization
    time.sleep(0.5)
    
    # Send a note command: B5 A4 00 DD 01 0F B0 (Middle C)
    print("Sending UART command to play Middle C...")
    command = [0xB5, 0xA4, 0x00, 0xDD, 0x01, 0x0F, 0xB0]
    for byte in command:
        cpu.uart_receive(byte)
    
    time.sleep(2)
    
    print(ay.get_state_string())
    
    # Send stop command
    print("\nSending stop command...")
    command = [0xB5, 0xA6, 0xB0]
    for byte in command:
        cpu.uart_receive(byte)
    
    time.sleep(0.5)
    
    # Stop
    running[0] = False
    time.sleep(0.1)
    audio.stop()
    
    print("Done!\n")


def main():
    """Run all examples"""
    print("=" * 60)
    print("8051 + AY-3-8910 Emulator - Usage Examples")
    print("=" * 60)
    print()
    
    try:
        # Run examples
        example_1_simple_tone()
        
        input("Press Enter to continue to next example...")
        print()
        
        example_2_chord()
        
        input("Press Enter to continue to next example...")
        print()
        
        example_3_with_cpu()
        
        print("=" * 60)
        print("All examples completed!")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
