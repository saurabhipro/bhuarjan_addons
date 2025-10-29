# QR Code Microsite Setup Guide

## Overview
The Form 10 report now includes a QR code in the top-left corner that, when scanned, opens a mobile-friendly microsite displaying the survey details.

## Features
- **QR Code in PDF**: Each Form 10 report has a QR code in the top-left corner
- **Mobile Microsite**: Scanned QR codes open a responsive web page
- **Survey Details**: Displays all survey information in a mobile-friendly format
- **PDF Download**: Direct download link for the full PDF report
- **Public Access**: No login required to view survey details

## Installation Requirements

### 1. Install QR Code Library
```bash
# In your Odoo virtual environment
pip install qrcode[pil]
```

### 2. Enable Website Module
The system requires the `website` module to be installed and enabled.

### 3. Update Module
After installation, update the bhuarjan module:
```bash
python3 odoo-bin -d bhuarjan1 -u bhuarjan --stop-after-init
```

## How It Works

### 1. QR Code Generation
- Each survey has a unique UUID (`survey_uuid` field)
- QR code contains URL: `http://your-domain.com/form10/{survey_uuid}`
- QR code appears in top-left corner of Form 10 PDF

### 2. Microsite Access
- Scan QR code with any smartphone camera or QR scanner app
- Opens mobile-friendly webpage with survey details
- No authentication required (public access)

### 3. Mobile Features
- Responsive design for mobile devices
- Survey details in card format
- Landowner information
- Land type details with green "Yes" indicators
- Direct PDF download button

## URL Structure

### Microsite URL
```
https://bhuarjan.com/form10/{survey_uuid}
```

### PDF Download URL
```
https://bhuarjan.com/form10/{survey_uuid}/pdf
```

## Example URLs
- Microsite: `https://bhuarjan.com/form10/abc123-def456-ghi789`
- PDF Download: `https://bhuarjan.com/form10/abc123-def456-ghi789/pdf`

## Security Considerations
- Survey data is publicly accessible via QR code
- Consider adding authentication if sensitive data is involved
- UUIDs are not easily guessable but are not encrypted

## Troubleshooting

### QR Code Not Generating
- Ensure `qrcode[pil]` library is installed
- Check virtual environment activation
- Verify website module is installed

### Microsite Not Loading
- Check URL structure matches controller routes
- Verify survey UUID exists in database
- Check Odoo server logs for errors

### PDF Download Issues
- Ensure report action exists: `bhuarjan.action_report_form10_survey`
- Check file permissions
- Verify survey data integrity

## Customization

### Change QR Code URL
Update the URL in `form10_survey_report.xml`:
```xml
<t t-set="qr_url" t-value="'https://bhuarjan.com/form10/' + survey.survey_uuid"/>
```

### Modify Microsite Design
Edit `qr_microsite_templates.xml` to customize:
- Layout and styling
- Information displayed
- Mobile responsiveness
- Branding elements

### Add Authentication
Modify controller routes to require authentication:
```python
@http.route('/form10/<string:survey_uuid>', type='http', auth='user', website=True)
```
