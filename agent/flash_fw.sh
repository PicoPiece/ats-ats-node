#!/bin/bash
# Flash firmware to ESP32 device
# Usage: ./agent/flash_fw.sh firmware.bin

set -e

FW_FILE="${1:-firmware.bin}"

if [ ! -f "$FW_FILE" ]; then
    echo "❌ Error: Firmware file '$FW_FILE' not found"
    exit 1
fi

echo "[ATS] Flashing firmware: $FW_FILE"
echo "[ATS] Target: ESP32"

# TODO: Implement actual flashing logic
# Example for ESP-IDF:
# idf.py -p /dev/ttyUSB0 flash

# For now, just verify file exists
if [ -f "$FW_FILE" ]; then
    echo "✅ Firmware file verified: $FW_FILE"
    echo "   Size: $(stat -c%s "$FW_FILE") bytes"
    echo "   SHA256: $(sha256sum "$FW_FILE" | awk '{print $1}')"
else
    echo "❌ Firmware file not found"
    exit 1
fi

echo "[ATS] Flash completed (simulated)"

