# Live QR Microsite Deployment Checklist

## Files to Deploy to Production Server

### 1. Controller File
**File:** `bhuarjan/controllers/qr_microsite.py`
**Purpose:** Handles QR code microsite routes
**Routes:**
- `/form10/{survey_uuid}` - Microsite page
- `/form10/{survey_uuid}/pdf` - PDF download

### 2. Template File  
**File:** `bhuarjan/views/qr_microsite_templates.xml`
**Purpose:** Mobile-friendly microsite templates
**Templates:**
- `qr_form10_microsite` - Main microsite page
- `qr_form10_not_found` - Error page
- `qr_form10_error` - Error page

### 3. Updated Model
**File:** `bhuarjan/models/survey.py`
**Purpose:** QR code generation method
**Method:** `get_qr_code_data()` - Generates QR code image

### 4. Updated Manifest
**File:** `bhuarjan/__manifest__.py`
**Changes:** Added `website` dependency and `qr_microsite_templates.xml`

## Production Server Steps

### 1. Install Dependencies
```bash
pip install qrcode[pil]
```

### 2. Upload Files
Upload all modified files to production server

### 3. Update Module
```bash
python3 odoo-bin -d production_db -u bhuarjan --stop-after-init
```

### 4. Enable Website Module
Ensure `website` module is installed and enabled

### 5. Test QR Code
1. Generate Form 10 report
2. Scan QR code with phone
3. Verify microsite opens

## Current QR Code URL
`https://bhuarjan.com/form10/{survey_uuid}`

## Expected Result
When QR code is scanned, it should open:
`https://bhuarjan.com/form10/c1ee21a3-193d-47f3-a4a6-2a7edfb8b235`

## Troubleshooting
- **404 Error:** Microsite files not deployed
- **QR Not Generating:** qrcode library missing
- **Module Error:** Module not updated properly
