# Mergington High School Activities API

A FastAPI application for browsing extracurricular activities, managing registrations, and publishing school announcements.

## Features

- View all available extracurricular activities
- Sign up and unregister students for activities (teacher login required)
- Display active announcements from MongoDB
- Manage announcements (create, edit, delete) for signed-in users

## Getting Started

1. Install the dependencies:

   ```
   pip install fastapi uvicorn
   ```

2. Run the application:

   ```
   python app.py
   ```

3. Open your browser and go to:
   - API documentation: http://localhost:8000/docs
   - Alternative documentation: http://localhost:8000/redoc

## API Endpoints

| Method | Endpoint | Description |
| ------ | -------- | ----------- |
| GET | `/activities` | Get all activities with optional schedule filters |
| POST | `/activities/{activity_name}/signup?email=student@mergington.edu&teacher_username=principal` | Register a student for an activity |
| POST | `/activities/{activity_name}/unregister?email=student@mergington.edu&teacher_username=principal` | Unregister a student from an activity |
| POST | `/auth/login?username=principal&password=admin789` | Teacher login |
| GET | `/auth/check-session?username=principal` | Validate a teacher session |
| GET | `/announcements` | Get active, non-expired announcements for public display |
| GET | `/announcements/manage?teacher_username=principal` | Get all announcements for management (requires sign-in) |
| POST | `/announcements?teacher_username=principal` | Create announcement (JSON body with message, expiration_date, optional start_date) |
| PUT | `/announcements/{announcement_id}?teacher_username=principal` | Update announcement (same JSON body as create) |
| DELETE | `/announcements/{announcement_id}?teacher_username=principal` | Delete announcement |

## Data Model

The application uses MongoDB collections:

1. **Activities** - Uses activity name as identifier:

   - Description
   - Schedule
   - Maximum number of participants allowed
   - List of student emails who are signed up

2. **Teachers** - Uses username as identifier:
   - Display name
   - Argon2 hashed password
   - Role

3. **Announcements** - Uses MongoDB ObjectId:
   - Message
   - Optional start date
   - Required expiration date
   - Created/updated metadata

Example data is initialized in `backend/database.py` when collections are empty.
