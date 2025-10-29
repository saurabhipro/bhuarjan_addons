# QR Microsite Deployment Guide

## Production Deployment Steps

### 1. Upload Files to Production Server
Copy these files to your production server:
- `bhuarjan/controllers/qr_microsite.py`
- `bhuarjan/views/qr_microsite_templates.xml`
- Updated `bhuarjan/models/survey.py`
- Updated `bhuarjan/__manifest__.py`

### 2. Install Dependencies
On production server:
```bash
pip install qrcode[pil]
```

### 3. Update Module
In Odoo production environment:
```bash
python3 odoo-bin -d production_db -u bhuarjan --stop-after-init
```

### 4. Enable Website Module
Ensure the `website` module is installed and enabled on production.

### 5. Test QR Code
1. Generate a Form 10 report
2. Scan the QR code
3. Verify it opens the microsite

## Development vs Production

### Development (Current)
- **QR URL:** `http://localhost:8069/form10/{uuid}`
- **Use Case:** Local testing and development
- **Access:** Only works on local machine

### Production (Target)
- **QR URL:** `https://bhuarjan.com/form10/{uuid}`
- **Use Case:** Field deployment and public access
- **Access:** Works from anywhere in the world

## Troubleshooting

### 404 Error
- **Cause:** Microsite routes not deployed to production
- **Solution:** Deploy controller and templates to production server

### QR Code Not Generating
- **Cause:** qrcode library not installed
- **Solution:** `pip install qrcode[pil]`

### Module Not Updating
- **Cause:** Module not properly updated
- **Solution:** Restart Odoo server and update module

## Current Status
- ✅ QR code generation working locally
- ✅ Microsite templates created
- ✅ Controller routes defined
- ❌ Production deployment pending
- ❌ Production server needs microsite files
