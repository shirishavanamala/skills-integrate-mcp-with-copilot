"""
High School Management System API

A super simple FastAPI application that allows students to view extracurricular
activities and authorized staff to manage signups.
"""

import base64
import binascii
import hashlib
import hmac
import os
import time
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from pydantic import BaseModel
from pathlib import Path

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

ADMIN_SESSION_COOKIE = "admin_session"
ADMIN_SESSION_TTL = 8 * 60 * 60
PASSWORD_HASH_ITERATIONS = 600_000


class AdminCredentials(BaseModel):
    username: str
    password: str


def _password_matches(password: str, encoded_hash: str) -> bool:
    """Verify a PBKDF2-SHA256 password hash from the environment."""
    try:
        algorithm, iterations, salt, expected_hash = encoded_hash.split("$")
        iteration_count = int(iterations)
        if algorithm != "pbkdf2_sha256" or iteration_count < PASSWORD_HASH_ITERATIONS:
            return False
        actual_hash = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt), iteration_count
        ).hex()
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual_hash, expected_hash)


def _session_token(username: str, secret: str) -> str:
    expires_at = int(time.time()) + ADMIN_SESSION_TTL
    payload = f"{username}|{expires_at}".encode()
    signature = hmac.new(secret.encode(), payload, hashlib.sha256).digest()
    encoded_payload = base64.urlsafe_b64encode(payload).decode().rstrip("=")
    return f"{encoded_payload}.{signature.hex()}"


def _session_username(token: str | None, secret: str) -> str | None:
    if not token:
        return None
    try:
        encoded_payload, encoded_signature = token.split(".", 1)
        payload = base64.urlsafe_b64decode(
            encoded_payload + "=" * (-len(encoded_payload) % 4)
        )
        signature = bytes.fromhex(encoded_signature)
        expected_signature = hmac.new(
            secret.encode(), payload, hashlib.sha256
        ).digest()
        if not hmac.compare_digest(signature, expected_signature):
            return None
        username, expires_at = payload.decode().rsplit("|", 1)
        if int(expires_at) <= int(time.time()):
            return None
        return username
    except (ValueError, UnicodeDecodeError, binascii.Error):
        return None


def _configured_admin() -> tuple[str, str, str]:
    username = os.getenv("ADMIN_USERNAME")
    password_hash = os.getenv("ADMIN_PASSWORD_HASH")
    session_secret = os.getenv("ADMIN_SESSION_SECRET")
    if not username or not password_hash or not session_secret:
        raise HTTPException(
            status_code=503,
            detail="Admin authentication is not configured",
        )
    return username, password_hash, session_secret


def require_admin(request: Request) -> str:
    configured_username, _, session_secret = _configured_admin()
    session_username = _session_username(
        request.cookies.get(ADMIN_SESSION_COOKIE), session_secret
    )
    if session_username != configured_username:
        raise HTTPException(status_code=401, detail="Admin sign-in required")
    return session_username


# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

# In-memory activity database
activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return activities


@app.get("/admin/session")
def get_admin_session(request: Request):
    try:
        username, _, session_secret = _configured_admin()
    except HTTPException as error:
        if error.status_code != 503:
            raise
        return {"authenticated": False}
    session_username = _session_username(
        request.cookies.get(ADMIN_SESSION_COOKIE), session_secret
    )
    return {"authenticated": session_username == username}


@app.post("/admin/login")
def login(credentials: AdminCredentials, response: Response):
    username, password_hash, session_secret = _configured_admin()
    username_matches = hmac.compare_digest(credentials.username, username)
    password_matches = _password_matches(credentials.password, password_hash)
    if not username_matches or not password_matches:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    response.set_cookie(
        key=ADMIN_SESSION_COOKIE,
        value=_session_token(username, session_secret),
        max_age=ADMIN_SESSION_TTL,
        httponly=True,
        secure=os.getenv("ADMIN_COOKIE_SECURE", "true").lower() == "true",
        samesite="strict",
        path="/",
    )
    return {"message": "Signed in"}


@app.post("/admin/logout")
def logout(response: Response):
    response.delete_cookie(
        key=ADMIN_SESSION_COOKIE,
        httponly=True,
        secure=os.getenv("ADMIN_COOKIE_SECURE", "true").lower() == "true",
        samesite="strict",
        path="/",
    )
    return {"message": "Signed out"}


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str, _: str = Depends(require_admin)):
    """Sign up a student for an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is not already signed up
    if email in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is already signed up"
        )

    # Add student
    activity["participants"].append(email)
    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(
    activity_name: str, email: str, _: str = Depends(require_admin)
):
    """Unregister a student from an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is signed up
    if email not in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity"
        )

    # Remove student
    activity["participants"].remove(email)
    return {"message": f"Unregistered {email} from {activity_name}"}
