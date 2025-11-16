# How to Upload Files to S3 Using Presigned URLs

## Step-by-Step Guide

### Step 1: Generate Presigned URL

**API Endpoint:** `POST /api/bhuarjan/s3/presigned-urls`

**Request Body:**
```json
{
    "survey_id": 193,
    "file_names": ["image1.jpg", "document1.pdf"]
}
```

**Response:**
```json
{
    "success": true,
    "data": {
        "presigned_urls": [
            {
                "file_name": "image1.jpg",
                "presigned_url": "https://bhuarjan.s3.amazonaws.com/surveys/193/image1.jpg?X-Amz-Algorithm=...",
                "s3_key": "surveys/193/image1.jpg",
                "bucket_name": "bhuarjan",
                "expires_in": 3600,
                "expires_at": "2025-11-16T18:40:00+00:00"
            }
        ],
        "total_files": 1,
        "successful": 1,
        "failed": 0,
        "survey_id": 193
    }
}
```

### Step 2: Upload File Using Presigned URL

#### Option A: Using Postman

1. **Create a new PUT request**
2. **Set the URL** to the `presigned_url` from Step 1 response
3. **Set Auth to "No Auth"** (IMPORTANT: Do not use Bearer token or any auth)
4. **Set Method to PUT**
5. **In Body tab:**
   - Select "binary" mode
   - Click "Select File" and choose your image file
6. **Set Headers:**
   - `Content-Type: image/jpeg` (or appropriate type: `image/png`, `application/pdf`, etc.)
7. **Send the request**

#### Option B: Using cURL

```bash
curl -X PUT \
  "https://bhuarjan.s3.amazonaws.com/surveys/193/image1.jpg?X-Amz-Algorithm=..." \
  -H "Content-Type: image/jpeg" \
  --data-binary "@/path/to/your/image.jpg"
```

#### Option C: Using JavaScript (Fetch API)

```javascript
const presignedUrl = "https://bhuarjan.s3.amazonaws.com/surveys/193/image1.jpg?X-Amz-Algorithm=...";
const file = document.getElementById('fileInput').files[0]; // or File object

fetch(presignedUrl, {
    method: 'PUT',
    headers: {
        'Content-Type': file.type // e.g., 'image/jpeg', 'image/png', 'application/pdf'
    },
    body: file
})
.then(response => {
    if (response.ok) {
        console.log('File uploaded successfully!');
    } else {
        console.error('Upload failed:', response.statusText);
    }
})
.catch(error => {
    console.error('Error:', error);
});
```

#### Option D: Using Python (requests library)

```python
import requests

presigned_url = "https://bhuarjan.s3.amazonaws.com/surveys/193/image1.jpg?X-Amz-Algorithm=..."
file_path = "/path/to/your/image.jpg"

with open(file_path, 'rb') as file:
    headers = {
        'Content-Type': 'image/jpeg'  # or 'image/png', 'application/pdf', etc.
    }
    response = requests.put(presigned_url, data=file, headers=headers)
    
    if response.status_code == 200:
        print("File uploaded successfully!")
    else:
        print(f"Upload failed: {response.status_code} - {response.text}")
```

## Important Notes

1. **No Authorization Header**: Do NOT include any `Authorization` header when uploading to presigned URLs. The URL already contains all authentication.

2. **Content-Type**: Set the appropriate `Content-Type` header:
   - `image/jpeg` for .jpg files
   - `image/png` for .png files
   - `application/pdf` for .pdf files
   - `application/octet-stream` for unknown types

3. **HTTP Method**: Always use **PUT** method (not POST)

4. **URL Validity**: Presigned URLs expire after 1 hour. Generate a new one if expired.

5. **File Size**: Make sure your file size is within S3 limits (5GB for single upload)

## Common Errors and Solutions

### Error: "Only one auth mechanism allowed"
- **Solution**: Remove the `Authorization` header from your request

### Error: "AccessDenied"
- **Solution**: Check AWS IAM permissions for the user. The user needs `s3:PutObject` permission.

### Error: "SignatureDoesNotMatch"
- **Solution**: The presigned URL may have expired. Generate a new one.

### Error: "403 Forbidden"
- **Solution**: Check that the S3 bucket name and AWS credentials are correct in Bhuarjan Settings Master.

## Example: Complete Flow

1. **Get presigned URL:**
   ```bash
   curl -X POST https://bhuarjan.com/api/bhuarjan/s3/presigned-urls \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     -d '{"survey_id": 193, "file_names": ["photo.jpg"]}'
   ```

2. **Upload file:**
   ```bash
   curl -X PUT "PRESIGNED_URL_FROM_STEP_1" \
     -H "Content-Type: image/jpeg" \
     --data-binary "@photo.jpg"
   ```

3. **Verify upload:**
   - Check S3 bucket: `bhuarjan/surveys/193/photo.jpg`
   - Or use S3 console to verify the file exists

