#!/usr/bin/env python3

"""
Quick QR code decoder for ODK Central managed QR codes

Usage: python3 decode-qr.py <image-file>

Install dependencies:
pip install pyzbar pillow zlib (usually builtin)
"""

import sys
import json
import base64
import zlib
from pathlib import Path

try:
    from pyzbar.pyzbar import decode
    from PIL import Image
except ImportError:
    print("❌ Missing dependencies. Install with:")
    print("  pip install pyzbar pillow")
    sys.exit(1)


def decode_qr(image_path):
    """Decode QR code from image and display the settings."""

    image_path = Path(image_path)
    if not image_path.exists():
        print(f"❌ File not found: {image_path}")
        sys.exit(1)

    try:
        # Open image and decode QR code
        image = Image.open(image_path)
        qr_codes = decode(image)

        if not qr_codes:
            print("❌ No QR code found in image")
            sys.exit(1)

        print("✅ QR Code detected!\n")

        # Get the QR code data (should be base64 encoded + zlib deflated JSON)
        qr_data = qr_codes[0].data.decode('utf-8')

        print("Raw QR Data (base64):")
        preview = qr_data[:100] + ("..." if len(qr_data) > 100 else "")
        print(preview)
        print(f"Length: {len(qr_data)} chars\n")

        # Decode from base64
        compressed_data = base64.b64decode(qr_data)

        # Decompress with zlib
        decompressed = zlib.decompress(compressed_data).decode('utf-8')

        # Parse JSON
        settings = json.loads(decompressed)

        print("📋 Decoded QR Payload (JSON):")
        print(json.dumps(settings, indent=2))

        print(f"\n✨ Payload size: {len(decompressed)} bytes")
        print(f"Compressed size: {len(compressed_data)} bytes")
        ratio = (1 - len(compressed_data) / len(decompressed)) * 100
        print(f"Compression ratio: {ratio:.1f}%")

        # Validate the payload structure
        print("\n📊 Payload structure check:")
        if 'general' in settings:
            print(f"  ✓ general: {len(settings['general'])} fields")
            for key in ['server_url', 'username', 'form_update_mode', 'automatic_update']:
                if key in settings['general']:
                    print(f"    ✓ {key}: {settings['general'][key]}")

        if 'admin' in settings:
            print(f"  ✓ admin: {len(settings['admin'])} fields")
            for key, val in settings['admin'].items():
                print(f"    ✓ {key}: {val}")

        if 'project' in settings:
            print(f"  ✓ project: {len(settings['project'])} fields")
            for key, val in settings['project'].items():
                print(f"    ✓ {key}: {val}")

    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in QR payload: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error decoding QR code: {e}")
        sys.exit(1)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 decode-qr.py <image-file>")
        print("Example: python3 decode-qr.py qr-code.png")
        sys.exit(1)

    decode_qr(sys.argv[1])
