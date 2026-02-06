#!/usr/bin/env python3
"""
Command Generator - Generate UART command sequences for testing

This script helps generate command sequences to test the 8051 sound CPU
and AY-3-8910 PSG system.
"""

def format_bytes(byte_list):
    """Format a list of bytes for display"""
    hex_str = " ".join(f"{b:02X}" for b in byte_list)
    dec_str = " ".join(f"{b:3d}" for b in byte_list)
    return f"Hex: {hex_str}\nDec: {dec_str}"

def cmd_play_note(channel, freq_low, freq_high, amplitude):
    """
    Generate command to play a note
    
    Args:
        channel: 0-2 (A, B, C)
        freq_low: Low byte of frequency period (0-255)
        freq_high: High byte of frequency period (0-15)
        amplitude: Volume (0-15)
    
    Returns:
        List of bytes
    """
    return [0xB5, 0xA4, channel & 0x0F, freq_low & 0xFF, 
            freq_high & 0x0F, amplitude & 0x0F, 0xB0]

def cmd_set_freq_low(channel, value):
    """Generate command to set frequency low byte"""
    return [0xB6, 0xA2, channel & 0x0F, value & 0xFF, 0xB0]

def cmd_set_freq_high(channel, value):
    """Generate command to set frequency high byte"""
    return [0xB5, 0xA3, channel & 0x0F, value & 0x0F, 0xB0]

def cmd_stop_all():
    """Generate command to stop all channels"""
    return [0xB5, 0xA6, 0xB0]

def freq_to_period(freq_hz, clock_freq=2000000):
    """Convert frequency in Hz to AY-3-8910 period value"""
    if freq_hz == 0:
        return 0
    return int(clock_freq / (16 * freq_hz))

def period_to_bytes(period):
    """Convert period to (low_byte, high_byte)"""
    return (period & 0xFF, (period >> 8) & 0x0F)

def note_to_freq(note_name):
    """
    Convert note name to frequency
    
    Args:
        note_name: String like "C4", "A4", "G#5", etc.
        
    Returns:
        Frequency in Hz
    """
    # Note frequencies for octave 4 (middle octave)
    notes = {
        'C': 261.63, 'C#': 277.18, 'Db': 277.18,
        'D': 293.66, 'D#': 311.13, 'Eb': 311.13,
        'E': 329.63,
        'F': 349.23, 'F#': 369.99, 'Gb': 369.99,
        'G': 392.00, 'G#': 415.30, 'Ab': 415.30,
        'A': 440.00, 'A#': 466.16, 'Bb': 466.16,
        'B': 493.88,
    }
    
    # Parse note name
    note = note_name[:-1] if note_name[-1].isdigit() else note_name
    octave = int(note_name[-1]) if note_name[-1].isdigit() else 4
    
    if note not in notes:
        raise ValueError(f"Unknown note: {note}")
    
    # Get base frequency and adjust for octave
    base_freq = notes[note]
    freq = base_freq * (2 ** (octave - 4))
    
    return freq

def generate_note_command(channel, note_name, amplitude=12):
    """
    Generate command to play a musical note
    
    Args:
        channel: 0-2 (A, B, C)
        note_name: String like "C4", "A4", etc.
        amplitude: Volume (0-15)
    
    Returns:
        List of bytes
    """
    freq = note_to_freq(note_name)
    period = freq_to_period(freq)
    low, high = period_to_bytes(period)
    return cmd_play_note(channel, low, high, amplitude)


def main():
    """Generate example command sequences"""
    
    print("=" * 70)
    print("8051 SOUND CPU - COMMAND SEQUENCE GENERATOR")
    print("=" * 70)
    
    print("\n1. PLAY MIDDLE C (C4, 262 Hz) ON CHANNEL A")
    print("-" * 70)
    cmd = generate_note_command(0, "C4", 15)
    print(format_bytes(cmd))
    print(f"Note: C4, Frequency: {note_to_freq('C4'):.2f} Hz, "
          f"Period: {freq_to_period(note_to_freq('C4'))}")
    
    print("\n2. PLAY A440 ON CHANNEL B")
    print("-" * 70)
    cmd = generate_note_command(1, "A4", 12)
    print(format_bytes(cmd))
    print(f"Note: A4, Frequency: {note_to_freq('A4'):.2f} Hz, "
          f"Period: {freq_to_period(note_to_freq('A4'))}")
    
    print("\n3. PLAY C MAJOR CHORD (C4-E4-G4)")
    print("-" * 70)
    for i, note in enumerate(["C4", "E4", "G4"]):
        cmd = generate_note_command(i, note, 10)
        print(f"Channel {chr(ord('A')+i)}: {note}")
        print(format_bytes(cmd))
        print()
    
    print("\n4. PLAY C MAJOR SCALE (C4 to C5)")
    print("-" * 70)
    scale = ["C4", "D4", "E4", "F4", "G4", "A4", "B4", "C5"]
    for note in scale:
        cmd = generate_note_command(0, note, 12)
        print(f"{note:3s}: {format_bytes(cmd).split(chr(10))[0]}")
    
    print("\n5. SET FREQUENCY LOW BYTE (Channel 1, value 0x44)")
    print("-" * 70)
    cmd = cmd_set_freq_low(1, 0x44)
    print(format_bytes(cmd))
    
    print("\n6. SET FREQUENCY HIGH BYTE (Channel 2, value 0x03)")
    print("-" * 70)
    cmd = cmd_set_freq_high(2, 0x03)
    print(format_bytes(cmd))
    
    print("\n7. STOP ALL CHANNELS")
    print("-" * 70)
    cmd = cmd_stop_all()
    print(format_bytes(cmd))
    
    print("\n8. OCTAVE TEST (Play A from octave 2 to 6)")
    print("-" * 70)
    for octave in range(2, 7):
        note = f"A{octave}"
        freq = note_to_freq(note)
        period = freq_to_period(freq)
        cmd = generate_note_command(0, note, 12)
        print(f"{note}: {freq:7.2f} Hz, Period: {period:4d}, "
              f"Cmd: {' '.join(f'{b:02X}' for b in cmd)}")
    
    print("\n9. CHROMATIC SCALE (C4 to B4)")
    print("-" * 70)
    chromatic = ["C4", "C#4", "D4", "D#4", "E4", "F4", 
                 "F#4", "G4", "G#4", "A4", "A#4", "B4"]
    for note in chromatic:
        freq = note_to_freq(note)
        period = freq_to_period(freq)
        low, high = period_to_bytes(period)
        print(f"{note:4s}: {freq:6.2f} Hz, Period: {period:4d} "
              f"(0x{high:01X}{low:02X}), Bytes: {low:3d} {high:3d}")
    
    print("\n10. COMPLETE TEST SEQUENCE")
    print("-" * 70)
    print("Send this sequence to test the system:")
    print()
    
    sequence = []
    # Play note on each channel
    sequence.extend(generate_note_command(0, "C4", 12))
    sequence.extend(generate_note_command(1, "E4", 12))
    sequence.extend(generate_note_command(2, "G4", 12))
    # Stop all
    sequence.extend(cmd_stop_all())
    
    print(format_bytes(sequence))
    print()
    print("This sequence:")
    print("  1. Plays C4 on channel A")
    print("  2. Plays E4 on channel B")
    print("  3. Plays G4 on channel C")
    print("  4. Stops all channels")
    
    print("\n" + "=" * 70)
    print("FREQUENCY REFERENCE TABLE")
    print("=" * 70)
    print()
    print("Note  | Freq (Hz) | Period | Low | High | Amplitude 12 Command")
    print("------+-----------+--------+-----+------+------------------------")
    
    for octave in range(3, 6):
        for note in ["C", "D", "E", "F", "G", "A", "B"]:
            note_name = f"{note}{octave}"
            freq = note_to_freq(note_name)
            period = freq_to_period(freq)
            low, high = period_to_bytes(period)
            cmd = generate_note_command(0, note_name, 12)
            cmd_str = " ".join(f"{b:02X}" for b in cmd)
            print(f"{note_name:5s} | {freq:9.2f} | {period:6d} | "
                  f"{low:3d} | {high:4d} | {cmd_str}")


if __name__ == "__main__":
    main()
