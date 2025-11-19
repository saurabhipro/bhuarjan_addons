# S3 Presigned URL Upload Guide

## The Problem

When uploading to S3 using a presigned URL, you get this error:
```
Only one auth mechanism allowed; only the X-Amz-Algorithm query parameter, 
Signature query string parameter or the Authorization header should be specified
```

**Root Cause:** You're sending an `Authorization: Bearer <token>` header along with the presigned URL. The presigned URL already contains all authentication in the query parameters, so AWS rejects requests with both.

## Solution: Remove Authorization Header

When uploading to a presigned URL, you must:
1. **NOT include any Authorization header**
2. Use **PUT method** (not GET or POST)
3. Set the correct **Content-Type header**

## Step-by-Step Upload Process

### Step 1: Generate Presigned URL

**API:** `POST /api/bhuarjan/s3/presigned-urls`

**Request:**
```json
{
    "survey_id": 257,
    "file_names": ["image1.jpg"]
}
```

**Response:**
```json
{
    "success": true,
    "data": {
        "file_name": "image1.jpg",
        "presigned_url": "https://bhuarjan.s3.amazonaws.com/surveys/257/image1.jpg?X-Amz-Algorithm=...",
        "content_type": "image/jpeg",
        "s3_key": "surveys/257/image1.jpg",
        "expires_in": 3600
    }
}
```

### Step 2: Upload File to S3

Use the `presigned_url` from Step 1 to upload directly to S3.

## Upload Examples

### Using Python (requests library) - CORRECT ✅

```python
import requests

# Get presigned URL from your API
presigned_url = "https://bhuarjan.s3.amazonaws.com/surveys/257/image1.jpg?X-Amz-Algorithm=..."

# Read your image file
with open('path/to/image.jpg', 'rb') as file:
    headers = {
        'Content-Type': 'image/jpeg'  # Use content_type from API response
    }
    # NO Authorization header!
    response = requests.put(presigned_url, data=file, headers=headers)
    
    if response.status_code == 200:
        print("Upload successful!")
        # The file is now at: https://bhuarjan.s3.amazonaws.com/surveys/257/image1.jpg
    else:
        print(f"Upload failed: {response.status_code}")
        print(response.text)
```

### Using Python (requests) - WRONG ❌

```python
# WRONG - Don't do this!
headers = {
    'Content-Type': 'image/jpeg',
    'Authorization': 'Bearer your-token'  # ❌ This causes the error!
}
response = requests.put(presigned_url, data=file, headers=headers)
```

### Using JavaScript (Fetch API) - CORRECT ✅

```javascript
const presignedUrl = "https://bhuarjan.s3.amazonaws.com/surveys/257/image1.jpg?X-Amz-Algorithm=...";
const file = document.getElementById('fileInput').files[0]; // File object

fetch(presignedUrl, {
    method: 'PUT',  // Must be PUT
    headers: {
        'Content-Type': 'image/jpeg'  // Match the content_type from API
        // NO Authorization header!
    },
    body: file
})
.then(response => {
    if (response.ok) {
        console.log('Upload successful!');
    } else {
        console.error('Upload failed:', response.statusText);
        return response.text().then(text => console.error(text));
    }
})
.catch(error => console.error('Error:', error));
```

### Using cURL - CORRECT ✅

```bash
curl -X PUT \
  "https://bhuarjan.s3.amazonaws.com/surveys/257/image1.jpg?X-Amz-Algorithm=..." \
  -H "Content-Type: image/jpeg" \
  --data-binary "@/path/to/your/image.jpg"
```

### Using Postman - CORRECT ✅

1. **Method:** PUT (not GET or POST)
2. **URL:** Paste the entire `presigned_url` from API response
3. **Auth Tab:** Select "No Auth" (IMPORTANT!)
4. **Headers:**
   - `Content-Type: image/jpeg` (use the `content_type` from API response)
5. **Body Tab:** 
   - Select "binary"
   - Choose your file
6. **Send**

## Comparison: Presigned URL vs Direct Upload

### Your Working Code (Direct Upload with Credentials)

```python
import boto3
import base64

def _upload_image_field_to_s3(self, field_name, s3_filename):
    # Direct upload using AWS credentials
    # IMPORTANT: Replace these with your actual AWS credentials from settings
    AWS_ACCESS_KEY = 'YOUR_AWS_ACCESS_KEY'  # Get from bhuarjan.settings.master
    AWS_SECRET_KEY = 'YOUR_AWS_SECRET_KEY'  # Get from bhuarjan.settings.master
    AWS_REGION = 'ap-south-1'  # Get from bhuarjan.settings.master
    S3_BUCKET_NAME = 'bhuarjan'  # Get from bhuarjan.settings.master
    
    s3_client = boto3.client(
        's3',
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
        region_name=AWS_REGION
    )
    
    decoded_image = base64.b64decode(image_data)
    s3_key = f"{s3_filename}.jpg"
    
    s3_client.put_object(
        Bucket=S3_BUCKET_NAME,
        Key=s3_key,
        Body=decoded_image,
        ContentType='image/jpeg'
    )
    
    return f"https://{S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{s3_key}"
```

**This works because:**
- You're using AWS credentials directly
- No presigned URL involved
- boto3 handles authentication automatically

### Presigned URL Upload (Client-Side)

```python
import requests

# Step 1: Get presigned URL from your API
response = requests.post(
    'https://bhuarjan.com/api/bhuarjan/s3/presigned-urls',
    json={'survey_id': 257, 'file_names': ['image1.jpg']},
    headers={'Authorization': 'Bearer your-token'}  # ✅ Auth needed for YOUR API
)
presigned_data = response.json()['data']
presigned_url = presigned_data['presigned_url']
content_type = presigned_data['content_type']

# Step 2: Upload to S3 using presigned URL
with open('image.jpg', 'rb') as file:
    response = requests.put(
        presigned_url,
        data=file,
        headers={'Content-Type': content_type}
        # ❌ NO Authorization header here!
    )
```

**Key Differences:**
1. **Your API** (`/api/bhuarjan/s3/presigned-urls`) - Needs Authorization header
2. **S3 Presigned URL** - NO Authorization header (authentication is in the URL)

## Common Mistakes

### ❌ Mistake 1: Including Authorization Header
```python
# WRONG
headers = {
    'Content-Type': 'image/jpeg',
    'Authorization': 'Bearer token'  # ❌ Causes "Only one auth mechanism" error
}
```

### ❌ Mistake 2: Using Wrong HTTP Method
```python
# WRONG - Presigned URLs are generated for PUT
response = requests.get(presigned_url, ...)  # ❌ Wrong method
response = requests.post(presigned_url, ...)  # ❌ Wrong method
```

### ❌ Mistake 3: Wrong Content-Type
```python
# WRONG - Must match what was used when generating presigned URL
headers = {'Content-Type': 'application/octet-stream'}  # ❌ If presigned URL was for image/jpeg
```

## Complete Working Example

```python
import requests
import base64

def upload_image_to_s3_via_presigned_url(survey_id, image_base64, filename):
    """
    Upload image to S3 using presigned URL workflow
    """
    # Step 1: Get presigned URL from your API
    api_url = f"https://bhuarjan.com/api/bhuarjan/s3/presigned-urls"
    api_response = requests.post(
        api_url,
        json={
            'survey_id': survey_id,
            'file_names': [filename]
        },
        headers={
            'Content-Type': 'application/json',
            'Authorization': 'Bearer your-jwt-token'  # ✅ Auth for YOUR API
        }
    )
    
    if api_response.status_code != 200:
        raise Exception(f"Failed to get presigned URL: {api_response.text}")
    
    presigned_data = api_response.json()['data']
    presigned_url = presigned_data['presigned_url']
    content_type = presigned_data['content_type']
    
    # Step 2: Decode base64 image
    image_data = base64.b64decode(image_base64)
    
    # Step 3: Upload to S3 using presigned URL
    upload_response = requests.put(
        presigned_url,
        data=image_data,
        headers={
            'Content-Type': content_type
            # ✅ NO Authorization header for S3!
        }
    )
    
    if upload_response.status_code == 200:
        # Construct final S3 URL
        s3_url = f"https://bhuarjan.s3.amazonaws.com/{presigned_data['s3_key']}"
        return s3_url
    else:
        raise Exception(f"Upload failed: {upload_response.status_code} - {upload_response.text}")

# Usage
survey_id = 257
image_base64 = "iVBORw0KGgoAAAANSUhEUgAA..."  # Your base64 image
filename = "image1.jpg"

try:
    s3_url = upload_image_to_s3_via_presigned_url(survey_id, image_base64, filename)
    print(f"Image uploaded successfully: {s3_url}")
except Exception as e:
    print(f"Error: {e}")
```

## Summary

**When calling YOUR API** (`/api/bhuarjan/s3/presigned-urls`):
- ✅ Include `Authorization: Bearer <token>` header

**When uploading to S3 presigned URL**:
- ❌ Do NOT include `Authorization` header
- ✅ Use PUT method
- ✅ Set correct Content-Type header
- ✅ Send file as binary data in body

The presigned URL contains all authentication needed - adding an Authorization header conflicts with it.

