# Bhuarjan REST API - Postman Collection

This Postman collection contains all the REST API endpoints for the Bhuarjan mobile app integration.

## Setup

1. **Import the Collection**
   - Open Postman
   - Click "Import" button
   - Select `Bhuarjan_API_Collection.postman_collection.json`
   - The collection will be imported with all endpoints

2. **Configure Base URL**
   - The collection uses a variable `{{base_url}}` which defaults to `http://localhost:8069`
   - To change it:
     - Click on the collection name
     - Go to "Variables" tab
     - Update the `base_url` value (e.g., `http://your-server:8069`)

## API Endpoints

### 1. Projects & Villages

#### Get All Projects and Villages
- **Method:** GET
- **URL:** `/api/bhuarjan/user/projects`
- **Description:** Returns all projects and their associated villages
- **Query Parameters (optional):**
  - `user_id` (integer) - Filter by user ID. If provided, only returns projects and villages mapped to that user. If not provided, returns all projects and villages.

### 2. Users

#### Get All Users
- **Method:** GET
- **URL:** `/api/bhuarjan/users`
- **Description:** Returns all users with their details including villages, tehsils, districts, and roles
- **Query Parameters (all optional):**
  - `limit` (integer) - Number of records (default: 100)
  - `offset` (integer) - Skip records (default: 0)
  - `role` (string) - Filter by bhuarjan_role: `patwari`, `revenue_inspector`, `nayab_tahsildar`, `tahsildar`, `sdm`, `additional_collector`, `collector`, `administrator`, `sia_team_member`

### 3. Departments

#### Get All Departments
- **Method:** GET
- **URL:** `/api/bhuarjan/departments`
- **Description:** Returns all departments with their details
- **Query Parameters (all optional):**
  - `limit` (integer) - Number of records (default: 100)
  - `offset` (integer) - Skip records (default: 0)

### 4. Surveys

#### Create Survey
- **Method:** POST
- **URL:** `/api/bhuarjan/survey`
- **Description:** Creates a new survey
- **Body:** JSON with survey fields
- **Required Fields:**
  - `project_id` (integer)
  - `village_id` (integer)
  - `department_id` (integer)
  - `tehsil_id` (integer)
  - `khasra_number` (string)
  - `total_area` (float)
  - `acquired_area` (float)
  - `survey_date` (string, format: YYYY-MM-DD)

#### Get Survey Details
- **Method:** GET
- **URL:** `/api/bhuarjan/survey/{survey_id}`
- **Description:** Get detailed information about a specific survey
- **Parameters:** Replace `{survey_id}` with actual survey ID

#### List Surveys
- **Method:** GET
- **URL:** `/api/bhuarjan/surveys`
- **Query Parameters (all optional):**
  - `project_id` (integer) - Filter by project
  - `village_id` (integer) - Filter by village
  - `state` (string) - Filter by state: `draft`, `submitted`, `approved`, `rejected`
  - `limit` (integer) - Number of records (default: 100)
  - `offset` (integer) - Skip records (default: 0)

### 5. Form 10 (Section 4 Notification)

#### Download Form 10 PDF
- **Method:** GET
- **URL:** `/api/bhuarjan/form10/download`
- **Description:** Downloads Form 10 (Section 4 Notification) PDF
- **Query Parameters (choose one):**
  - Option 1: `project_id` + `village_id`
  - Option 2: `notification_id`

### 6. Landowners

#### Create Landowner
- **Method:** POST
- **URL:** `/api/bhuarjan/landowner`
- **Description:** Creates a new landowner
- **Body:** JSON with landowner fields
- **Required Fields:**
  - `name` (string)
  - `village_id` (integer)
  - `gender` (string: `male`, `female`, `other`)

## Sample Data

**Important:** Before testing, you need to get actual IDs from your Odoo database:

1. **Get Project ID:**
   - Call `GET /api/bhuarjan/user/projects`
   - Note the `id` of the project you want to use

2. **Get Village ID:**
   - From the projects response, note the `id` of a village

3. **Get Department ID:**
   - You can find this in Odoo UI: Settings > Master Data > Departments
   - Or query the database directly

4. **Get Tehsil ID:**
   - You can find this in Odoo UI: Settings > Master Data > Tehsils
   - Or query the database directly

5. **Update Sample Requests:**
   - Replace all placeholder IDs (like `1`, `2`, `3`) in the Postman collection with actual IDs from your database

## Testing Tips

1. **Start with Get Projects:**
   - First, call `GET /api/bhuarjan/user/projects` to see available projects and villages
   - Use the IDs from this response in other requests

2. **Create Landowner First:**
   - Before creating a survey, create a landowner
   - Use the returned landowner ID in the survey's `landowner_ids` array

3. **Create Survey:**
   - Use the project_id, village_id, department_id, and tehsil_id from the projects endpoint
   - Use the landowner_id from the create landowner response

4. **Test Form 10 Download:**
   - Ensure a Section 4 Notification exists for the project and village
   - Use the notification_id or project_id + village_id to download

## Notes

- All APIs are **public** (no authentication required)
- All APIs use `auth='public'` and `csrf=False`
- Replace all sample IDs with actual IDs from your database
- Date format: `YYYY-MM-DD` (e.g., `2024-12-15`)
- DateTime format: `YYYY-MM-DD HH:MM:SS` (e.g., `2024-12-15 10:30:00`)

## Error Handling

All endpoints return JSON responses with:
- `success: true/false`
- `data: {...}` (on success)
- `error: "error message"` (on failure)

HTTP Status Codes:
- `200` - Success
- `201` - Created
- `400` - Bad Request
- `404` - Not Found
- `500` - Internal Server Error

