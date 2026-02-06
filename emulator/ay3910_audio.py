#!/usr/bin/env python3
"""
AY-3-8910 Sound Chip Emulator with Real Audio Output

This module provides a complete emulation of the AY-3-8910 Programmable Sound
Generator with real-time audio synthesis.
"""

import numpy as np
import threading
import queue
import time


class AY3910Audio:
    """AY-3-8910 sound chip emulator with audio output"""
    
    def __init__(self, clock_freq=2000000, sample_rate=44100):
        """
        Initialize AY-3-8910 audio emulator
        
        Args:
            clock_freq: Master clock frequency in Hz (default 2 MHz)
            sample_rate: Audio sample rate in Hz (default 44100)
        """
        self.clock_freq = clock_freq
        self.sample_rate = sample_rate
        
        # AY-3-8910 registers (16 total)
        self.registers = [0] * 16
        self.address_latch = 0
        
        # Tone generators (3 channels)
        self.tone_counters = [0, 0, 0]
        self.tone_outputs = [0, 0, 0]
        
        # Noise generator
        self.noise_counter = 0
        self.noise_output = 0
        self.noise_lfsr = 1  # 17-bit LFSR
        
        # Envelope generator
        self.envelope_counter = 0
        self.envelope_output = 0
        self.envelope_step = 0
        
        # Audio buffer
        self.audio_buffer = queue.Queue(maxsize=4096)
        
        # Clock divider for audio generation
        self.clock_divider = int(clock_freq / sample_rate / 16)
        self.clock_counter = 0
        
        # Initialize mixer to silence all channels
        self.registers[7] = 0b00111111  # All channels disabled
        
    def latch_address(self, address):
        """Latch register address"""
        self.address_latch = address & 0x0F
        
    def write_data(self, data):
        """Write data to latched register"""
        if 0 <= self.address_latch < 16:
            self.registers[self.address_latch] = data & 0xFF
            
    def read_data(self):
        """Read data from latched register"""
        if 0 <= self.address_latch < 16:
            return self.registers[self.address_latch]
        return 0xFF
        
    def set_channel_frequency(self, channel, period):
        """Set frequency period for a channel (12-bit value)"""
        if 0 <= channel <= 2:
            reg_base = channel * 2
            self.registers[reg_base] = period & 0xFF
            self.registers[reg_base + 1] = (period >> 8) & 0x0F
            
    def get_channel_frequency(self, channel):
        """Get frequency period for a channel"""
        if 0 <= channel <= 2:
            reg_base = channel * 2
            return self.registers[reg_base] | (self.registers[reg_base + 1] << 8)
        return 0
        
    def set_channel_amplitude(self, channel, amplitude):
        """Set amplitude for a channel (0-15 or envelope mode)"""
        if 0 <= channel <= 2:
            self.registers[8 + channel] = amplitude & 0x1F
            
    def get_channel_amplitude(self, channel):
        """Get amplitude for a channel"""
        if 0 <= channel <= 2:
            return self.registers[8 + channel]
        return 0
        
    def set_mixer(self, mixer_value):
        """Set mixer control register"""
        self.registers[7] = mixer_value & 0xFF
        
    def enable_channel_tone(self, channel, enable=True):
        """Enable or disable tone for a channel"""
        if 0 <= channel <= 2:
            if enable:
                self.registers[7] &= ~(1 << channel)
            else:
                self.registers[7] |= (1 << channel)
                
    def enable_channel_noise(self, channel, enable=True):
        """Enable or disable noise for a channel"""
        if 0 <= channel <= 2:
            if enable:
                self.registers[7] &= ~(1 << (3 + channel))
            else:
                self.registers[7] |= (1 << (3 + channel))
                
    def frequency_to_period(self, freq_hz):
        """Convert frequency in Hz to period value"""
        if freq_hz == 0:
            return 0
        return int(self.clock_freq / (16 * freq_hz))
        
    def period_to_frequency(self, period):
        """Convert period value to frequency in Hz"""
        if period == 0:
            return 0
        return self.clock_freq / (16 * period)
        
    def update_tone_generator(self, channel):
        """Update tone generator for a channel"""
        period = self.get_channel_frequency(channel)
        if period == 0:
            period = 1
            
        self.tone_counters[channel] -= 1
        if self.tone_counters[channel] <= 0:
            self.tone_counters[channel] = period
            self.tone_outputs[channel] ^= 1
            
    def update_noise_generator(self):
        """Update noise generator"""
        noise_period = self.registers[6] & 0x1F
        if noise_period == 0:
            noise_period = 1
            
        self.noise_counter -= 1
        if self.noise_counter <= 0:
            self.noise_counter = noise_period
            # 17-bit LFSR for white noise
            bit = ((self.noise_lfsr >> 0) ^ (self.noise_lfsr >> 3)) & 1
            self.noise_lfsr = ((self.noise_lfsr >> 1) | (bit << 16)) & 0x1FFFF
            self.noise_output = bit
            
    def get_channel_output(self, channel):
        """Get output level for a channel"""
        # Check if tone is enabled
        tone_enabled = (self.registers[7] & (1 << channel)) == 0
        # Check if noise is enabled
        noise_enabled = (self.registers[7] & (1 << (3 + channel))) == 0
        
        # Combine tone and noise
        output = 0
        if tone_enabled and self.tone_outputs[channel]:
            output = 1
        if noise_enabled and self.noise_output:
            output = 1
            
        if not tone_enabled and not noise_enabled:
            output = 0
            
        # Get amplitude
        amp_reg = self.registers[8 + channel]
        if amp_reg & 0x10:
            # Envelope mode
            amplitude = self.envelope_output
        else:
            # Fixed amplitude
            amplitude = amp_reg & 0x0F
            
        return output * amplitude
        
    def generate_sample(self):
        """Generate one audio sample"""
        # Update generators at 1/16th of clock frequency
        for _ in range(16):
            for ch in range(3):
                self.update_tone_generator(ch)
            self.update_noise_generator()
            
        # Mix channels
        sample = 0.0
        for ch in range(3):
            level = self.get_channel_output(ch)
            sample += level / 15.0  # Normalize to 0-1 range
            
        # Scale to 3 channels and apply volume
        sample = sample / 3.0
        
        return sample
        
    def clock(self):
        """Clock the sound chip and generate audio samples"""
        self.clock_counter += 1
        if self.clock_counter >= self.clock_divider:
            self.clock_counter = 0
            sample = self.generate_sample()
            
            # Add to audio buffer if not full
            if not self.audio_buffer.full():
                self.audio_buffer.put(sample)
                
    def get_audio_data(self, num_samples):
        """Get audio samples from buffer"""
        samples = []
        for _ in range(num_samples):
            try:
                samples.append(self.audio_buffer.get_nowait())
            except queue.Empty:
                # If buffer is empty, add silence
                samples.append(0.0)
        return np.array(samples, dtype=np.float32)
        
    def get_state_string(self):
        """Get human-readable state"""
        lines = ["AY-3-8910 State:"]
        lines.append("=" * 60)
        
        for ch in range(3):
            ch_name = chr(ord('A') + ch)
            period = self.get_channel_frequency(ch)
            amp = self.get_channel_amplitude(ch)
            freq = self.period_to_frequency(period) if period > 0 else 0
            
            tone_enabled = (self.registers[7] & (1 << ch)) == 0
            noise_enabled = (self.registers[7] & (1 << (3 + ch))) == 0
            
            lines.append(f"Channel {ch_name}:")
            lines.append(f"  Period: {period:4d} (0x{period:03X})")
            lines.append(f"  Frequency: {freq:7.2f} Hz")
            lines.append(f"  Amplitude: {amp:2d} (0x{amp:02X})")
            lines.append(f"  Tone: {'ON' if tone_enabled else 'OFF'}, "
                        f"Noise: {'ON' if noise_enabled else 'OFF'}")
        
        lines.append("=" * 60)
        return "\n".join(lines)


class AudioOutput:
    """Audio output handler using PyAudio"""
    
    def __init__(self, ay_chip, sample_rate=44100):
        """
        Initialize audio output
        
        Args:
            ay_chip: AY3910Audio instance
            sample_rate: Audio sample rate
        """
        self.ay_chip = ay_chip
        self.sample_rate = sample_rate
        self.running = False
        self.stream = None
        self.pyaudio_instance = None
        
    def start(self):
        """Start audio output"""
        try:
            import pyaudio
            self.pyaudio_instance = pyaudio.PyAudio()
            
            def callback(in_data, frame_count, time_info, status):
                # Get audio data from AY chip
                data = self.ay_chip.get_audio_data(frame_count)
                return (data.tobytes(), pyaudio.paContinue)
            
            self.stream = self.pyaudio_instance.open(
                format=pyaudio.paFloat32,
                channels=1,
                rate=self.sample_rate,
                output=True,
                stream_callback=callback,
                frames_per_buffer=1024
            )
            
            self.stream.start_stream()
            self.running = True
            print("Audio output started")
            
        except ImportError:
            print("PyAudio not available - audio output disabled")
            print("Install with: pip install pyaudio")
            self.running = False
            
    def stop(self):
        """Stop audio output"""
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        if self.pyaudio_instance:
            self.pyaudio_instance.terminate()
        self.running = False
        print("Audio output stopped")
        
    def is_running(self):
        """Check if audio is running"""
        return self.running
