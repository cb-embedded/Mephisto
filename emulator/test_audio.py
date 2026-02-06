#!/usr/bin/env python3
"""
Test the emulator with pre-programmed music sequences
"""

import sys
import time
from cpu8051 import CPU8051
from ay3910_audio import AY3910Audio, AudioOutput


def test_basic():
    """Test basic emulator functionality without actual CPU"""
    print("=" * 60)
    print("Basic AY-3-8910 Audio Test")
    print("=" * 60)
    print()
    
    # Create AY chip
    ay_chip = AY3910Audio(clock_freq=2000000, sample_rate=44100)
    audio = AudioOutput(ay_chip, sample_rate=44100)
    
    # Start audio
    audio.start()
    if not audio.is_running():
        print("Audio not available - test will continue without sound")
    
    time.sleep(0.5)
    
    # Test 1: Play Middle C
    print("Test 1: Playing Middle C (262 Hz) for 1 second...")
    ay_chip.set_channel_frequency(0, 477)  # 262 Hz
    ay_chip.set_channel_amplitude(0, 15)
    ay_chip.enable_channel_tone(0, True)
    
    # Generate audio for 1 second
    samples_per_sec = 44100
    for _ in range(samples_per_sec // 16):
        for _ in range(16):
            ay_chip.clock()
    
    print(ay_chip.get_state_string())
    time.sleep(1)
    
    # Test 2: Play A440
    print("\nTest 2: Playing A440 for 1 second...")
    ay_chip.set_channel_frequency(1, 284)  # 440 Hz
    ay_chip.set_channel_amplitude(1, 12)
    ay_chip.enable_channel_tone(1, True)
    
    for _ in range(samples_per_sec // 16):
        for _ in range(16):
            ay_chip.clock()
    
    print(ay_chip.get_state_string())
    time.sleep(1)
    
    # Test 3: Play C Major Chord
    print("\nTest 3: Playing C Major Chord (C-E-G) for 2 seconds...")
    ay_chip.set_channel_frequency(0, 477)  # C = 262 Hz
    ay_chip.set_channel_amplitude(0, 10)
    ay_chip.enable_channel_tone(0, True)
    
    ay_chip.set_channel_frequency(1, 378)  # E = 330 Hz
    ay_chip.set_channel_amplitude(1, 10)
    ay_chip.enable_channel_tone(1, True)
    
    ay_chip.set_channel_frequency(2, 318)  # G = 392 Hz
    ay_chip.set_channel_amplitude(2, 10)
    ay_chip.enable_channel_tone(2, True)
    
    for _ in range(samples_per_sec * 2 // 16):
        for _ in range(16):
            ay_chip.clock()
    
    print(ay_chip.get_state_string())
    time.sleep(2)
    
    # Test 4: Silence
    print("\nTest 4: Silence all channels...")
    ay_chip.set_channel_amplitude(0, 0)
    ay_chip.set_channel_amplitude(1, 0)
    ay_chip.set_channel_amplitude(2, 0)
    
    print(ay_chip.get_state_string())
    time.sleep(0.5)
    
    # Stop audio
    audio.stop()
    
    print("\nBasic test complete!")
    print()


def test_melody():
    """Play a simple melody"""
    print("=" * 60)
    print("Melody Test")
    print("=" * 60)
    print()
    
    # Create AY chip
    ay_chip = AY3910Audio(clock_freq=2000000, sample_rate=44100)
    audio = AudioOutput(ay_chip, sample_rate=44100)
    
    # Start audio
    audio.start()
    if not audio.is_running():
        print("Audio not available - test will continue without sound")
    
    time.sleep(0.5)
    
    # Define a simple melody: C D E F G A B C
    notes = [
        ("C4", 262, 477),
        ("D4", 294, 425),
        ("E4", 330, 378),
        ("F4", 349, 358),
        ("G4", 392, 318),
        ("A4", 440, 284),
        ("B4", 494, 253),
        ("C5", 523, 238),
    ]
    
    print("Playing C major scale...")
    print()
    
    samples_per_sec = 44100
    note_duration = 0.5  # seconds
    
    for name, freq_hz, period in notes:
        print(f"Playing {name} ({freq_hz} Hz)...")
        
        # Set note
        ay_chip.set_channel_frequency(0, period)
        ay_chip.set_channel_amplitude(0, 12)
        ay_chip.enable_channel_tone(0, True)
        
        # Generate audio
        for _ in range(int(samples_per_sec * note_duration) // 16):
            for _ in range(16):
                ay_chip.clock()
        
        time.sleep(note_duration)
        
        # Brief silence between notes
        ay_chip.set_channel_amplitude(0, 0)
        for _ in range(int(samples_per_sec * 0.05) // 16):
            for _ in range(16):
                ay_chip.clock()
        time.sleep(0.05)
    
    # Final silence
    ay_chip.set_channel_amplitude(0, 0)
    time.sleep(0.5)
    
    # Stop audio
    audio.stop()
    
    print("\nMelody test complete!")
    print()


def main():
    """Run tests"""
    print("8051 + AY-3-8910 Emulator Test Suite")
    print()
    
    # Run basic test
    test_basic()
    
    print("\n" + "=" * 60)
    input("Press Enter to play a melody test...")
    print()
    
    # Run melody test
    test_melody()
    
    print("All tests complete!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nTests interrupted by user")
        sys.exit(0)
