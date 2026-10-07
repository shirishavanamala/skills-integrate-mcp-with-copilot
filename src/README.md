# Mergington High School Activities API

A super simple FastAPI application that allows students to view and sign up for extracurricular activities.

## Features

- View all available extracurricular activities
- Publicly view activity participants
- Require staff sign-in to register or unregister students

## Getting Started

1. Install the dependencies:

   ```
   pip install fastapi uvicorn
   ```

2. Configure a staff account and a signing secret in the server environment. Generate a PBKDF2-SHA256 password hash and a session secret with:

   ```
   python -c "import getpass, hashlib, secrets; password = getpass.getpass(); salt = secrets.token_bytes(16); digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 600000).hex(); print(f'pbkdf2_sha256$600000${salt.hex()}${digest}')"
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

   Set `ADMIN_USERNAME`, `ADMIN_PASSWORD_HASH` to the first command's output, and `ADMIN_SESSION_SECRET` to the second command's output. Supply these values through your deployment's secret manager or environment configuration; do not commit them. For local development over plain HTTP only, set `ADMIN_COOKIE_SECURE=false`. The cookie is secure by default and should remain secure in deployed environments.

3. Run the application:

   ```
   uvicorn app:app --app-dir src --reload
   ```

4. Open your browser and go to:
   - API documentation: http://localhost:8000/docs
   - Alternative documentation: http://localhost:8000/redoc
   - Activities page: http://localhost:8000/

## API Endpoints

| Method | Endpoint                                                          | Description                                                            |
| ------ | ----------------------------------------------------------------- | ---------------------------------------------------------------------- |
| GET    | `/activities`                                                     | Get all activities and current participants; no sign-in required       |
| GET    | `/admin/session`                                                  | Check whether the current browser has an active staff session           |
| POST   | `/admin/login`                                                    | Sign in with the configured staff username and password                |
| POST   | `/admin/logout`                                                   | Clear the current staff session                                         |
| POST   | `/activities/{activity_name}/signup?email=student@mergington.edu` | Register a student; requires staff sign-in                              |
| DELETE | `/activities/{activity_name}/unregister?email=student@mergington.edu` | Unregister a student; requires staff sign-in                         |

Staff sessions use an HttpOnly, SameSite=Strict signed cookie that expires after eight hours. Passwords are verified against a salted PBKDF2-SHA256 hash; neither passwords nor hashes are stored in the repository.

## Data Model

The application uses a simple data model with meaningful identifiers:

1. **Activities** - Uses activity name as identifier:

   - Description
   - Schedule
   - Maximum number of participants allowed
   - List of student emails who are signed up

2. **Students** - Uses email as identifier:
   - Name
   - Grade level

Activity data is stored in memory, which means changes will be reset when the server restarts.
