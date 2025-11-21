# Bhuarjan Survey API - Usage Guide

## Overview

This guide explains how to use the Survey API endpoint to create and update surveys with tree information.

## Base URL

The API base URL depends on your server configuration:
- **Local Development**: `http://localhost:8069`
- **Production**: `https://your-domain.com` (configured in your Odoo instance)

## Endpoint

**Create Survey**: `POST /api/bhuarjan/survey`

**Update Survey**: `PATCH /api/bhuarjan/survey/{survey_id}`

## Authentication

The API requires authentication. Include your JWT token in the request headers:

```
Authorization: Bearer YOUR_JWT_TOKEN
```

## Request Headers

```
Content-Type: application/json
Authorization: Bearer YOUR_JWT_TOKEN
```

## Create Survey Request

### Required Fields

- `project_id` (integer): Project ID
- `village_id` (integer): Village ID
- `department_id` (integer): Department ID
- `tehsil_id` (integer): Tehsil ID
- `khasra_number` (string): Khasra number
- `total_area` (float): Total area in hectares
- `acquired_area` (float): Acquired area in hectares
- `landowner_ids` (array): Array of landowner IDs (at least one required)

### Tree Lines - Important Update

**`development_stage` is now REQUIRED for ALL trees** (both fruit-bearing and non-fruit-bearing).

Each tree in the `tree_lines` array must include:
- `tree_type`: `"fruit_bearing"` or `"non_fruit_bearing"`
- Either `tree_master_id` (integer) OR `tree_name` (string) to identify the tree
- `quantity` (integer): Number of trees (default: 1)
- **`development_stage` (string, REQUIRED)**: One of:
  - `"undeveloped"` - Undeveloped / अविकसित
  - `"semi_developed"` - Semi-developed / अर्ध-विकसित
  - `"fully_developed"` - Fully Developed / पूर्ण विकसित
- For **non-fruit-bearing trees only**:
  - `girth_cm` (float, optional): Tree girth in centimeters (must be > 0 if provided)

## Example Request

### Using cURL

```bash
curl -X POST "http://localhost:8069/api/bhuarjan/survey" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "project_id": 3,
    "village_id": 1,
    "department_id": 2,
    "tehsil_id": 1,
    "khasra_number": "103",
    "total_area": 2.5,
    "acquired_area": 2.0,
    "has_traded_land": "no",
    "traded_land_area": 0.0,
    "crop_type": 11,
    "irrigation_type": "irrigated",
    "has_house": "no",
    "house_type": "pakka",
    "house_area": 0.0,
    "has_shed": "yes",
    "shed_area": 100.0,
    "has_well": "yes",
    "well_type": "pakka",
    "has_tubewell": "no",
    "has_pond": "no",
    "latitude": 21.8974,
    "longitude": 83.3960,
    "location_accuracy": 10.5,
    "location_timestamp": "2024-12-15 10:30:00",
    "remarks": "Survey completed successfully",
    "state": "draft",
    "landowner_ids": [316],
    "tree_lines": [
        {
            "tree_type": "fruit_bearing",
            "tree_master_id": 1,
            "development_stage": "fully_developed",
            "quantity": 5
        },
        {
            "tree_type": "non_fruit_bearing",
            "tree_master_id": 2,
            "development_stage": "semi_developed",
            "girth_cm": 50.5,
            "quantity": 10
        }
    ]
}'
```

### Using Python (requests library)

```python
import requests
import json

url = "http://localhost:8069/api/bhuarjan/survey"
headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer YOUR_JWT_TOKEN"
}

data = {
    "project_id": 3,
    "village_id": 1,
    "department_id": 2,
    "tehsil_id": 1,
    "khasra_number": "103",
    "total_area": 2.5,
    "acquired_area": 2.0,
    "has_traded_land": "no",
    "traded_land_area": 0.0,
    "crop_type": 11,
    "irrigation_type": "irrigated",
    "has_house": "no",
    "house_type": "pakka",
    "house_area": 0.0,
    "has_shed": "yes",
    "shed_area": 100.0,
    "has_well": "yes",
    "well_type": "pakka",
    "has_tubewell": "no",
    "has_pond": "no",
    "latitude": 21.8974,
    "longitude": 83.3960,
    "location_accuracy": 10.5,
    "location_timestamp": "2024-12-15 10:30:00",
    "remarks": "Survey completed successfully",
    "state": "draft",
    "landowner_ids": [316],
    "tree_lines": [
        {
            "tree_type": "fruit_bearing",
            "tree_master_id": 1,
            "development_stage": "fully_developed",
            "quantity": 5
        },
        {
            "tree_type": "non_fruit_bearing",
            "tree_master_id": 2,
            "development_stage": "semi_developed",
            "girth_cm": 50.5,
            "quantity": 10
        }
    ]
}

response = requests.post(url, headers=headers, json=data)
print(response.status_code)
print(response.json())
```

### Using JavaScript (fetch)

```javascript
const url = "http://localhost:8069/api/bhuarjan/survey";
const headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer YOUR_JWT_TOKEN"
};

const data = {
    project_id: 3,
    village_id: 1,
    department_id: 2,
    tehsil_id: 1,
    khasra_number: "103",
    total_area: 2.5,
    acquired_area: 2.0,
    has_traded_land: "no",
    traded_land_area: 0.0,
    crop_type: 11,
    irrigation_type: "irrigated",
    has_house: "no",
    house_type: "pakka",
    house_area: 0.0,
    has_shed: "yes",
    shed_area: 100.0,
    has_well: "yes",
    well_type: "pakka",
    has_tubewell: "no",
    has_pond: "no",
    latitude: 21.8974,
    longitude: 83.3960,
    location_accuracy: 10.5,
    location_timestamp: "2024-12-15 10:30:00",
    remarks: "Survey completed successfully",
    state: "draft",
    landowner_ids: [316],
    tree_lines: [
        {
            tree_type: "fruit_bearing",
            tree_master_id: 1,
            development_stage: "fully_developed",
            quantity: 5
        },
        {
            tree_type: "non_fruit_bearing",
            tree_master_id: 2,
            development_stage: "semi_developed",
            girth_cm: 50.5,
            quantity: 10
        }
    ]
};

fetch(url, {
    method: "POST",
    headers: headers,
    body: JSON.stringify(data)
})
.then(response => response.json())
.then(data => console.log(data))
.catch(error => console.error("Error:", error));
```

## Success Response (201 Created)

```json
{
    "success": true,
    "data": {
        "id": 257,
        "name": "SC_001_0001",
        "survey_uuid": "...",
        "khasra_number": "103",
        "state": "draft"
    }
}
```

## Error Response (400 Bad Request)

If `development_stage` is missing for any tree, you'll receive:

```json
{
    "error": "development_stage is required for all trees"
}
```

### Other Common Errors

**Missing Required Fields:**
```json
{
    "success": false,
    "error": "VALIDATION_ERROR",
    "error_code": "MISSING_REQUIRED_FIELDS",
    "message": "The following required fields are missing: Project, Village",
    "fields": ["project_id", "village_id"]
}
```

**Invalid development_stage:**
```json
{
    "error": "Invalid development_stage: invalid_value. Must be one of: undeveloped, semi_developed, fully_developed"
}
```

## Tree Line Examples

### Fruit-bearing Tree (development_stage is REQUIRED)

```json
{
    "tree_type": "fruit_bearing",
    "tree_master_id": 1,
    "development_stage": "fully_developed",
    "quantity": 5
}
```

### Non-fruit-bearing Tree (with girth)

```json
{
    "tree_type": "non_fruit_bearing",
    "tree_master_id": 2,
    "development_stage": "semi_developed",
    "girth_cm": 50.5,
    "quantity": 10
}
```

### Non-fruit-bearing Tree (without girth)

```json
{
    "tree_type": "non_fruit_bearing",
    "tree_master_id": 2,
    "development_stage": "undeveloped",
    "quantity": 10
}
```

## Important Notes

1. **`development_stage` is mandatory for ALL trees** - both fruit-bearing and non-fruit-bearing
2. Valid `development_stage` values are:
   - `"undeveloped"`
   - `"semi_developed"`
   - `"fully_developed"`
3. For non-fruit-bearing trees, `girth_cm` is optional but must be > 0 if provided
4. You can use either `tree_master_id` (integer) or `tree_name` (string) to identify the tree
5. The `quantity` field defaults to 1 if not provided

## Testing with Postman

1. Import the Postman collection: `bhuarjan/postman/Bhuarjan REST API.postman_collection.json`
2. Set the `base_url` variable to your server URL
3. Set up authentication with your JWT token
4. Use the "Create Survey" request and modify the JSON body as needed
5. Make sure all `tree_lines` include `development_stage`

