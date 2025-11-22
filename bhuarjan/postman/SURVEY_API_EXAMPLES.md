# Survey API - Sample Request Examples

## Create Survey API

**Endpoint:** `POST /api/bhuarjan/survey`

**Headers:**
```
Content-Type: application/json
Authorization: Bearer YOUR_JWT_TOKEN
```

### Sample Request 1: Complete Survey with All Fields

```json
{
  "project_id": 7,
  "village_id": 1,
  "department_id": 4,
  "tehsil_id": 1,
  "khasra_number": "1/03",
  "total_area": 2.5,
  "acquired_area": 2.0,
  "land_type_id": 1,
  "crop_type": 1,
  "irrigation_type": "irrigated",
  "tree_development_stage": "fully_developed",
  "tree_count": 25,
  "has_house": "no",
  "house_type": "pakka",
  "house_area": 0.0,
  "shed_area": 0.0,
  "has_well": "yes",
  "well_type": "pakka",
  "has_tubewell": "no",
  "has_pond": "no",
  "trees_description": "Mango and neem trees",
  "latitude": 21.8974,
  "longitude": 83.3960,
  "location_accuracy": 10.5,
  "location_timestamp": "2024-12-15 10:30:00",
  "remarks": "Survey completed successfully",
  "state": "submitted",
  "landowner_ids": [126]
}
```

### Sample Request 2: Minimal Required Fields

```json
{
  "project_id": 7,
  "village_id": 1,
  "department_id": 4,
  "tehsil_id": 1,
  "khasra_number": "1/03",
  "total_area": 2.5,
  "acquired_area": 2.0,
  "crop_type": 1,
  "irrigation_type": "irrigated",
  "landowner_ids": [126]
}
```

### Sample Request 3: With Survey Image (Base64)

```json
{
  "project_id": 7,
  "village_id": 1,
  "department_id": 4,
  "tehsil_id": 1,
  "khasra_number": "1/03",
  "total_area": 2.5,
  "acquired_area": 2.0,
  "crop_type": 1,
  "irrigation_type": "irrigated",
  "tree_development_stage": "fully_developed",
  "tree_count": 25,
  "has_house": "no",
  "has_well": "yes",
  "well_type": "pakka",
  "landowner_ids": [126],
  "survey_image": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEAYABgAAD...",
  "survey_image_filename": "survey_photo.jpg"
}
```

## Update Survey API (PATCH)

**Endpoint:** `PATCH /api/bhuarjan/survey/{survey_id}`

**Headers:**
```
Content-Type: application/json
Authorization: Bearer YOUR_JWT_TOKEN
```

### Sample Request: Update Crop Type

```json
{
  "crop_type": 2,
  "irrigation_type": "unirrigated",
  "tree_count": 30
}
```

### Sample Request: Update Multiple Fields

```json
{
  "crop_type": 1,
  "total_area": 3.0,
  "acquired_area": 2.5,
  "tree_count": 35,
  "remarks": "Updated survey information"
}
```

## Field Descriptions

### Required Fields:
- `project_id` (integer): Project ID
- `village_id` (integer): Village ID
- `department_id` (integer): Department ID
- `tehsil_id` (integer): Tehsil ID
- `khasra_number` (string): Khasra number
- `total_area` (float): Total area in hectares
- `acquired_area` (float): Acquired area in hectares
- `landowner_ids` (array of integers): Array of landowner IDs (at least one required)

### Optional Fields:
- `land_type_id` (integer): Land type ID from land type master
- `crop_type` (integer): **Crop type ID from land type master** (एक फसली=1, दो फसली=2, पड़ती=3)
- `irrigation_type` (string): "irrigated" or "unirrigated"
- `tree_development_stage` (string): "undeveloped", "semi_developed", or "fully_developed"
- `tree_count` (integer): Number of trees
- `has_house` (string): "yes" or "no"
- `house_type` (string): "pakka" or "kaccha"
- `house_area` (float): House area in square feet
- `shed_area` (float): Shed area in square feet
- `has_well` (string): "yes" or "no"
- `well_type` (string, optional): "pakka" or "kaccha"
- `has_tubewell` (string): "yes" or "no"
- `has_pond` (string): "yes" or "no"
- `trees_description` (string): Description of trees
- `latitude` (float): GPS latitude
- `longitude` (float): GPS longitude
- `location_accuracy` (float): Location accuracy in meters
- `location_timestamp` (string): Timestamp in format "YYYY-MM-DD HH:MM:SS"
- `remarks` (string): Additional remarks
- `state` (string): "submitted" (default for API), "draft", "approved", "rejected"
- `survey_date` (string, optional): Date in format "YYYY-MM-DD" (auto-computed if not provided)
- `survey_image` (string): Base64 encoded image (with data URL prefix)
- `survey_image_filename` (string): Filename for the survey image

## Crop Type Values (Land Type Master IDs)

To get the correct `crop_type` ID, first call the Land Types API:

**GET** `/api/bhuarjan/land-types`

Response example:
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "name": "एक फसली",
      "code": "SINGLE_CROP",
      "description": "Single crop land",
      "active": true
    },
    {
      "id": 2,
      "name": "दो फसली",
      "code": "DOUBLE_CROP",
      "description": "Double crop land",
      "active": true
    },
    {
      "id": 3,
      "name": "पड़ती",
      "code": "FALLOW",
      "description": "Fallow land",
      "active": true
    }
  ]
}
```

Then use the `id` value in your `crop_type` field:
- `"crop_type": 1` for एक फसली (Single crop)
- `"crop_type": 2` for दो फसली (Double crop)
- `"crop_type": 3` for पड़ती (Fallow)

## Response Example

```json
{
  "success": true,
  "data": {
    "id": 193,
    "name": "SC_RG_JUR_001",
    "survey_uuid": "550e8400-e29b-41d4-a716-446655440000",
    "project_id": 7,
    "project_name": "Ring Road Raigarh",
    "village_id": 1,
    "village_name": "जुर्दा",
    "department_id": 4,
    "department_name": "Public Works Department",
    "tehsil_id": 1,
    "tehsil_name": "Raigarh",
    "district_name": "Raigarh (Chhattisgarh)",
    "khasra_number": "1/03",
    "total_area": 2.5,
    "acquired_area": 2.0,
    "survey_date": "2024-12-15",
    "crop_type": 1,
    "crop_type_name": "एक फसली",
    "crop_type_code": "SINGLE_CROP",
    "irrigation_type": "irrigated",
    "tree_development_stage": "fully_developed",
    "tree_count": 25,
    "has_house": "no",
    "house_type": "pakka",
    "house_area": 0.0,
    "shed_area": 0.0,
    "has_well": "yes",
    "well_type": "pakka",
    "has_tubewell": "no",
    "has_pond": "no",
    "trees_description": "Mango and neem trees",
    "latitude": 21.8974,
    "longitude": 83.3960,
    "location_accuracy": 10.5,
    "location_timestamp": "2024-12-15 10:30:00",
    "remarks": "Survey completed successfully",
    "state": "submitted",
    "landowner_ids": [126],
    "landowner_count": 1
  }
}
```

