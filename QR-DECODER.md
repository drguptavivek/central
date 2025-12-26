# QR Code Decoder Scripts

Quick scripts to decode and validate ODK Central managed QR codes.

## Python Version (Recommended)

### Setup

```bash
pip install pyzbar pillow
```

### Usage

```bash
python3 decode-qr.py <image-file>

# Example:
python3 decode-qr.py qr-code.png
```

### Output

```
✅ QR Code detected!

Raw QR Data (base64):
eJyVUctuwzAM+xefiwW57NCfETRbSbz6Edhyuqzov09Ck3Qb...
Length: 342 chars

📋 Decoded QR Payload (JSON):
{
  "general": {
    "server_url": "https://central.local/v1/projects/1",
    "username": "data_collector",
    "form_update_mode": "match_exactly",
    "automatic_update": true,
    "delete_send": false,
    "default_completed": false,
    "analytics": true,
    "metadata_username": "John Doe"
  },
  "admin": {
    "change_server": false
  },
  "project": {
    "name": "Health Project",
    "project_id": "1"
  }
}

✨ Payload size: 245 bytes
Compressed size: 156 bytes
Compression ratio: 36.3%

📊 Payload structure check:
  ✓ general: 8 fields
    ✓ server_url: https://central.local/v1/projects/1
    ✓ username: data_collector
    ✓ form_update_mode: match_exactly
    ✓ automatic_update: true
  ✓ admin: 1 fields
    ✓ change_server: false
  ✓ project: 2 fields
    ✓ name: Health Project
    ✓ project_id: 1
```

## Node.js Version

### Setup

```bash
npm install jsqr pako jimp
```

### Usage

```bash
node decode-qr.js <image-file>

# Example:
node decode-qr.js qr-code.png
```

## How to Get QR Code Image

1. **Screenshot from browser:**
   - Open the app in browser
   - Click "Show QR" button on an app user
   - Right-click on the QR code → Save image as PNG

2. **From ODK Collect:**
   - When scanning a code, take a screenshot
   - Extract the QR code region to a PNG file

## Testing the Implementation

To verify managed QR codes are working correctly:

```bash
# Test password reset QR
python3 decode-qr.py screenshot-password-reset.png

# Test show QR button
python3 decode-qr.py screenshot-show-qr.png

# Both should have identical structure and contain username
```

## Payload Validation Checklist

- [ ] `general.server_url` includes full project path (`/v1/projects/{id}`)
- [ ] `general.username` is present and correct
- [ ] `general.form_update_mode` = `"match_exactly"`
- [ ] `general.automatic_update` = `true`
- [ ] `general.delete_send` = `false`
- [ ] `general.default_completed` = `false`
- [ ] `general.analytics` = `true`
- [ ] `general.metadata_username` = App user display name
- [ ] `admin.change_server` = `false`
- [ ] `project.name` = Project name
- [ ] `project.project_id` = Project ID
- [ ] No literal `"..."` fields in payload
- [ ] Payload is complete (not truncated)

## Troubleshooting

### "No QR code found in image"
- Image quality may be poor
- Try a clearer screenshot or higher resolution
- Ensure the entire QR code is visible

### "Invalid JSON in QR payload"
- QR payload may be corrupted
- Try regenerating the QR code

### "Payload contains '...'"
- This indicates the payload is being truncated
- Settings object is too large
- Need to reduce settings or use higher QR version
