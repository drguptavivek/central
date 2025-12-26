#!/usr/bin/env node

/**
 * Quick QR code decoder for ODK Central managed QR codes
 *
 * Usage: node decode-qr.js <image-file>
 *
 * Install dependencies:
 * npm install jsqr pako
 */

const fs = require('fs');
const path = require('path');
const jimp = require('jimp');
const jsQR = require('jsqr');
const pako = require('pako');

async function decodeQR(imagePath) {
  try {
    // Read image file
    const image = await jimp.read(imagePath);

    // Convert to grayscale for better QR detection
    const imageData = {
      data: new Uint8ClampedArray(image.bitmap.data),
      width: image.bitmap.width,
      height: image.bitmap.height
    };

    // Decode QR code
    const qrCode = jsQR(imageData.data, imageData.width, imageData.height);

    if (!qrCode) {
      console.error('❌ No QR code found in image');
      process.exit(1);
    }

    console.log('✅ QR Code detected!\n');

    // QR data is base64 encoded + zlib deflated JSON
    const base64Data = qrCode.data;
    console.log('Raw QR Data (base64):');
    console.log(base64Data.substring(0, 100) + (base64Data.length > 100 ? '...' : ''));
    console.log(`Length: ${base64Data.length} chars\n`);

    // Decode from base64
    const compressedData = Buffer.from(base64Data, 'base64');

    // Decompress with zlib
    const decompressed = pako.inflate(compressedData, { to: 'string' });

    // Parse JSON
    const settings = JSON.parse(decompressed);

    console.log('📋 Decoded QR Payload (JSON):');
    console.log(JSON.stringify(settings, null, 2));

    console.log('\n✨ Payload size:', decompressed.length, 'bytes');
    console.log('Compressed size:', base64Data.length, 'bytes');
    console.log(`Compression ratio: ${((1 - compressedData.length / decompressed.length) * 100).toFixed(1)}%`);

  } catch (error) {
    console.error('❌ Error decoding QR code:', error.message);
    process.exit(1);
  }
}

const args = process.argv.slice(2);
if (args.length === 0) {
  console.error('Usage: node decode-qr.js <image-file>');
  console.error('Example: node decode-qr.js qr-code.png');
  process.exit(1);
}

const imagePath = path.resolve(args[0]);
if (!fs.existsSync(imagePath)) {
  console.error(`❌ File not found: ${imagePath}`);
  process.exit(1);
}

decodeQR(imagePath);
