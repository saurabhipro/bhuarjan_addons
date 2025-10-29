# QR Code Test Script

## Test QR Code Generation

Run this in Odoo shell to test QR code generation:

```python
# Start Odoo shell
python3 odoo-bin shell -d bhuarjan1

# In the shell, run:
survey = env['bhu.survey'].search([], limit=1)
if survey:
    qr_data = survey.get_qr_code_data()
    if qr_data:
        print("QR code generated successfully!")
        print(f"QR code length: {len(qr_data)} characters")
    else:
        print("QR code generation failed")
else:
    print("No surveys found")
```

## Expected Output
- "QR code generated successfully!"
- QR code length should be several thousand characters (base64 encoded image)

## Troubleshooting

### If QR code still doesn't appear:
1. Check if qrcode library is installed: `pip list | grep qrcode`
2. Verify survey has survey_uuid: `survey.survey_uuid`
3. Check Odoo logs for any errors during report generation

### If QR code appears but doesn't scan:
1. Verify the URL is correct: `https://bhuarjan.com/form10/{uuid}`
2. Test the microsite URL manually in browser
3. Check if website module is installed and enabled
