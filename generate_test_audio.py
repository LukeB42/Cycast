#!/usr/bin/env python3
"""
Generate test audio file for Cycast testing
Creates a simple tone as MP3 using pydub
"""

import os
import sys

def create_test_mp3():
    """Create a test MP3 file with a simple tone"""
    try:
        from pydub import AudioSegment
        from pydub.generators import Sine
    except ImportError:
        print("pydub not installed. Trying alternative method...")
        create_test_mp3_raw()
        return
    
    print("Generating test MP3 file...")
    
    # Create a 10-second sine wave at 440 Hz (A note)
    duration_ms = 10000
    frequency = 440
    
    tone = Sine(frequency).to_audio_segment(duration=duration_ms)
    
    # Create music directory if it doesn't exist
    os.makedirs('music', exist_ok=True)
    
    # Export as MP3
    output_file = 'music/test_tone.mp3'
    tone.export(output_file, format='mp3', bitrate='128k')
    
    print(f"✓ Created {output_file}")
    print(f"  Duration: {duration_ms / 1000}s")
    print(f"  Frequency: {frequency} Hz")
    print(f"  Bitrate: 128 kbps")


def create_test_mp3_raw():
    """Create a minimal test MP3 without pydub"""
    print("Creating minimal test audio...")
    print("Note: This creates a silent MP3 frame for testing")
    
    # Minimal MP3 frame (silent)
    # This is a valid MP3 frame with MPEG-1 Layer 3, 128kbps, 44.1kHz
    mp3_frame = bytes([
        0xFF, 0xFB, 0x90, 0x00,  # MP3 sync + header
        0x00, 0x00, 0x00, 0x00,  # Additional header
        0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00,
    ])
    
    # Create music directory
    os.makedirs('music', exist_ok=True)
    
    # Write multiple frames to create a longer file
    output_file = 'music/test_silent.mp3'
    with open(output_file, 'wb') as f:
        # Write 1000 frames (~30 seconds)
        for _ in range(1000):
            f.write(mp3_frame)
    
    print(f"✓ Created {output_file}")
    print("  This is a minimal silent MP3 for testing")
    print("  Install pydub for better test files: pip install pydub")


def main():
    if '--help' in sys.argv or '-h' in sys.argv:
        print("Generate Test MP3 for Cycast")
        print()
        print("Usage: python generate_test_audio.py")
        print()
        print("Creates a test MP3 file in ./music/ directory")
        print("Requires pydub for tone generation, or creates silent MP3 otherwise")
        return
    
    try:
        create_test_mp3()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
