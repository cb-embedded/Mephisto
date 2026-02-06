#!/usr/bin/env python3
"""
Reference Implementation: 8051 Sound CPU + AY-3-8910 Emulator

This is a complete emulator for the sound system based on reverse engineering
of the sound_cpu_8051.bin firmware.

Usage:
    emulator = SoundSystemEmulator()
    
    # Send command bytes via UART
    for byte in [0xB5, 0xA4, 0x00, 0xDD, 0x01, 0x0F, 0xB0]:
        emulator.uart_receive(byte)
    
    # Process any pending commands
    emulator.process()
    
    # Get current AY-3-8910 state
    state = emulator.get_ay_state()
"""

class AY3810Emulator:
    """Emulator for the AY-3-8910 Programmable Sound Generator"""
    
    def __init__(self, clock_freq=2000000):
        """
        Initialize AY-3-8910 emulator
        
        Args:
            clock_freq: Master clock frequency in Hz (default 2 MHz)
        """
        self.clock_freq = clock_freq
        self.registers = [0] * 16
        self.address_latch = 0
        
        # Initialize to silent state
        self.registers[7] = 0b00111111  # All channels disabled
        
    def latch_address(self, address):
        """Latch a register address (BC1=1, BC2=1, BDIR=1)"""
        self.address_latch = address & 0x0F
        
    def write_data(self, data):
        """Write data to latched register (BC1=0, BC2=1, BDIR=1)"""
        if 0 <= self.address_latch < 16:
            self.registers[self.address_latch] = data & 0xFF
            
    def read_data(self):
        """Read data from latched register (BC1=1, BC2=1, BDIR=0)"""
        if 0 <= self.address_latch < 16:
            return self.registers[self.address_latch]
        return 0xFF
        
    def set_channel_frequency(self, channel, period):
        """
        Set frequency for a channel
        
        Args:
            channel: 0 (A), 1 (B), or 2 (C)
            period: 12-bit period value
        """
        if 0 <= channel <= 2:
            reg_base = channel * 2
            self.registers[reg_base] = period & 0xFF
            self.registers[reg_base + 1] = (period >> 8) & 0x0F
            
    def get_channel_frequency(self, channel):
        """Get frequency period for a channel"""
        if 0 <= channel <= 2:
            reg_base = channel * 2
            period = self.registers[reg_base] | (self.registers[reg_base + 1] << 8)
            return period
        return 0
        
    def set_channel_amplitude(self, channel, amplitude):
        """
        Set amplitude/volume for a channel
        
        Args:
            channel: 0 (A), 1 (B), or 2 (C)
            amplitude: 0-15 (0x00-0x0F), or 0x10-0x1F for envelope mode
        """
        if 0 <= channel <= 2:
            self.registers[8 + channel] = amplitude & 0x1F
            
    def get_channel_amplitude(self, channel):
        """Get amplitude for a channel"""
        if 0 <= channel <= 2:
            return self.registers[8 + channel]
        return 0
        
    def set_mixer(self, mixer_value):
        """Set mixer control register (R7)"""
        self.registers[7] = mixer_value & 0xFF
        
    def enable_channel_tone(self, channel, enable=True):
        """Enable or disable tone output for a channel"""
        if 0 <= channel <= 2:
            if enable:
                self.registers[7] &= ~(1 << channel)  # 0 = enabled
            else:
                self.registers[7] |= (1 << channel)   # 1 = disabled
                
    def enable_channel_noise(self, channel, enable=True):
        """Enable or disable noise output for a channel"""
        if 0 <= channel <= 2:
            if enable:
                self.registers[7] &= ~(1 << (3 + channel))  # 0 = enabled
            else:
                self.registers[7] |= (1 << (3 + channel))   # 1 = disabled
                
    def frequency_to_period(self, freq_hz):
        """Convert frequency in Hz to AY period value"""
        if freq_hz == 0:
            return 0
        return int(self.clock_freq / (16 * freq_hz))
        
    def period_to_frequency(self, period):
        """Convert AY period value to frequency in Hz"""
        if period == 0:
            return 0
        return self.clock_freq / (16 * period)
        
    def get_state_string(self):
        """Get human-readable state of all channels"""
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


class Sound8051Emulator:
    """Emulator for the 8051 MCU firmware that controls AY-3-8910"""
    
    # State machine states
    STATE_WAIT_START = 0
    STATE_RECEIVE_CMD = 1
    STATE_RECEIVE_DATA = 2
    
    def __init__(self, ay_chip):
        """
        Initialize 8051 emulator
        
        Args:
            ay_chip: AY3810Emulator instance
        """
        self.ay_chip = ay_chip
        self.state = self.STATE_WAIT_START
        self.start_marker = 0
        self.buffer = []
        self.data_ready_flag = False
        
    def uart_receive(self, byte):
        """
        Process a byte received via UART
        
        Args:
            byte: Received byte (0x00-0xFF)
        """
        if self.state == self.STATE_WAIT_START:
            # State 0: Look for start marker
            if byte in [0xB5, 0xB6]:
                self.start_marker = byte
                self.buffer = []
                self.state = self.STATE_RECEIVE_CMD
                
        elif self.state == self.STATE_RECEIVE_CMD:
            # State 1: Receive first data/command byte
            self.buffer.append(byte)
            self.state = self.STATE_RECEIVE_DATA
            
        elif self.state == self.STATE_RECEIVE_DATA:
            # State 2: Continue receiving data
            self.buffer.append(byte)
            
            # Check for end marker
            if byte == 0xB0:
                self.data_ready_flag = True
                self.state = self.STATE_WAIT_START
                
    def process(self):
        """
        Process any pending commands
        
        Returns:
            True if a command was processed, False otherwise
        """
        if not self.data_ready_flag or len(self.buffer) == 0:
            return False
            
        self.data_ready_flag = False
        
        # First byte is the command
        cmd = self.buffer[0]
        
        # Everything between command and end marker (0xB0) is data
        data = self.buffer[1:-1] if len(self.buffer) > 1 else []
        
        # Dispatch to command handler
        result = self._handle_command(cmd, data)
        
        # Clear buffer
        self.buffer = []
        
        return result
        
    def _handle_command(self, cmd, data):
        """Handle a specific command"""
        
        if cmd == 0xA0:
            # Status/control command
            return self._cmd_status(data)
            
        elif cmd == 0xA2:
            # Set frequency low byte
            return self._cmd_freq_low(data)
            
        elif cmd == 0xA3:
            # Set frequency high byte
            return self._cmd_freq_high(data)
            
        elif cmd == 0xA4:
            # Full note command (channel + freq + amplitude)
            return self._cmd_note(data)
            
        elif cmd == 0xA6:
            # Stop/silence command
            return self._cmd_stop(data)
            
        elif cmd == 0xA7:
            # Special command 1
            return self._cmd_special1(data)
            
        elif cmd == 0xA8:
            # Special command 2
            return self._cmd_special2(data)
            
        else:
            print(f"Unknown command: 0x{cmd:02X}")
            return False
            
    def _cmd_status(self, data):
        """Handle 0xA0 status command"""
        # Implementation depends on what status command does
        # For now, just return success
        return True
        
    def _cmd_freq_low(self, data):
        """Handle 0xA2 frequency low byte command"""
        if len(data) < 2:
            return False
            
        channel = data[0] & 0x0F
        freq_low = data[1]
        
        if channel > 2:
            return False
            
        # Get current period, update low byte
        current_period = self.ay_chip.get_channel_frequency(channel)
        new_period = (current_period & 0xFF00) | freq_low
        
        self.ay_chip.set_channel_frequency(channel, new_period)
        return True
        
    def _cmd_freq_high(self, data):
        """Handle 0xA3 frequency high byte command"""
        if len(data) < 2:
            return False
            
        channel = data[0] & 0x0F
        freq_high = data[1]
        
        if channel > 2:
            return False
            
        # Get current period, update high byte
        current_period = self.ay_chip.get_channel_frequency(channel)
        new_period = (freq_high << 8) | (current_period & 0x00FF)
        
        self.ay_chip.set_channel_frequency(channel, new_period)
        return True
        
    def _cmd_note(self, data):
        """Handle 0xA4 full note command"""
        if len(data) < 4:
            return False
            
        channel = data[0] & 0x0F
        freq_low = data[1]
        freq_high = data[2]
        amplitude = data[3]
        
        if channel > 2:
            return False
            
        # Set frequency period
        period = (freq_high << 8) | freq_low
        self.ay_chip.set_channel_frequency(channel, period)
        
        # Set amplitude
        self.ay_chip.set_channel_amplitude(channel, amplitude & 0x1F)
        
        # Enable tone output for this channel
        self.ay_chip.enable_channel_tone(channel, True)
        
        return True
        
    def _cmd_stop(self, data):
        """Handle 0xA6 stop command"""
        # Silence all channels by setting amplitude to 0
        for ch in range(3):
            self.ay_chip.set_channel_amplitude(ch, 0)
        return True
        
    def _cmd_special1(self, data):
        """Handle 0xA7 special command"""
        # Implementation depends on what this command does
        return True
        
    def _cmd_special2(self, data):
        """Handle 0xA8 special command"""
        # Implementation depends on what this command does
        return True


class SoundSystemEmulator:
    """Complete sound system emulator (8051 + AY-3-8910)"""
    
    def __init__(self, clock_freq=2000000):
        """
        Initialize sound system emulator
        
        Args:
            clock_freq: AY-3-8910 clock frequency in Hz
        """
        self.ay_chip = AY3810Emulator(clock_freq)
        self.mcu = Sound8051Emulator(self.ay_chip)
        
    def uart_receive(self, byte):
        """Send a byte to the UART"""
        self.mcu.uart_receive(byte)
        
    def uart_send_bytes(self, bytes_list):
        """Send multiple bytes to the UART"""
        for byte in bytes_list:
            self.uart_receive(byte)
            
    def process(self):
        """Process any pending commands"""
        return self.mcu.process()
        
    def process_all(self):
        """Process all pending commands"""
        count = 0
        while self.process():
            count += 1
        return count
        
    def get_ay_state(self):
        """Get current AY-3-8910 state as string"""
        return self.ay_chip.get_state_string()
        
    def play_note(self, channel, frequency_hz, amplitude):
        """
        Convenience method to play a note
        
        Args:
            channel: 0 (A), 1 (B), or 2 (C)
            frequency_hz: Frequency in Hz
            amplitude: Volume (0-15)
        """
        period = self.ay_chip.frequency_to_period(frequency_hz)
        period_low = period & 0xFF
        period_high = (period >> 8) & 0x0F
        
        cmd = [0xB5, 0xA4, channel, period_low, period_high, amplitude, 0xB0]
        self.uart_send_bytes(cmd)
        self.process()
        
    def stop_all(self):
        """Stop all channels"""
        cmd = [0xB5, 0xA6, 0xB0]
        self.uart_send_bytes(cmd)
        self.process()


def demo():
    """Demonstration of the emulator"""
    print("8051 Sound CPU + AY-3-8910 Emulator Demo")
    print("=" * 60)
    
    # Create emulator
    emu = SoundSystemEmulator(clock_freq=2000000)
    
    print("\n1. Playing Middle C (262 Hz) on Channel A")
    print("-" * 60)
    emu.play_note(channel=0, frequency_hz=262, amplitude=15)
    print(emu.get_ay_state())
    
    print("\n2. Playing A440 on Channel B")
    print("-" * 60)
    emu.play_note(channel=1, frequency_hz=440, amplitude=12)
    print(emu.get_ay_state())
    
    print("\n3. Playing C Major Chord (C-E-G)")
    print("-" * 60)
    emu.play_note(channel=0, frequency_hz=262, amplitude=10)  # C
    emu.play_note(channel=1, frequency_hz=330, amplitude=10)  # E
    emu.play_note(channel=2, frequency_hz=392, amplitude=10)  # G
    print(emu.get_ay_state())
    
    print("\n4. Sending raw command: [B5 A2 01 44 B0]")
    print("-" * 60)
    emu.uart_send_bytes([0xB5, 0xA2, 0x01, 0x44, 0xB0])
    emu.process()
    print(emu.get_ay_state())
    
    print("\n5. Stop all channels")
    print("-" * 60)
    emu.stop_all()
    print(emu.get_ay_state())
    
    print("\n6. Testing invalid command (should be ignored)")
    print("-" * 60)
    emu.uart_send_bytes([0xFF, 0xAA, 0xBB])  # Invalid start marker
    processed = emu.process()
    print(f"Command processed: {processed}")
    
    print("\nDemo complete!")


if __name__ == "__main__":
    demo()
