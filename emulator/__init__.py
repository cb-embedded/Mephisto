"""
8051 + AY-3-8910 Real-Time Music Emulator

This package provides a complete emulation of:
- 8051 microcontroller executing sound_cpu_8051.bin
- AY-3-8910 Programmable Sound Generator
- Real-time audio output
- UART input via stdin
"""

__version__ = "1.0.0"
__all__ = ['CPU8051', 'AY3910Audio', 'AudioOutput', 'SoundSystem']

from .cpu8051 import CPU8051
from .ay3910_audio import AY3910Audio, AudioOutput
from .main import SoundSystem
