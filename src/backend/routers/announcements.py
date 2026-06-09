"""
Announcement endpoints for the High School Management System API
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from bson import ObjectId
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..database import announcements_collection, teachers_collection

router = APIRouter(
    prefix="/announcements",
    tags=["announcements"]
)


class AnnouncementPayload(BaseModel):
    """Request payload for creating or updating announcements."""

    message: str
    expiration_date: str
    start_date: Optional[str] = None


def _parse_iso_datetime(value: Optional[str], field_name: str) -> Optional[datetime]:
    if value is None:
        return None

    try:
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid {field_name}") from exc

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc)


def _serialize_announcement(document: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(document["_id"]),
        "message": document["message"],
        "start_date": document.get("start_date"),
        "expiration_date": document["expiration_date"],
        "created_at": document.get("created_at"),
        "updated_at": document.get("updated_at"),
        "created_by": document.get("created_by")
    }


def _is_active_announcement(document: Dict[str, Any]) -> bool:
    now = datetime.now(timezone.utc)

    start_date = _parse_iso_datetime(document.get("start_date"), "start_date")
    expiration_date = _parse_iso_datetime(document.get("expiration_date"), "expiration_date")

    if expiration_date is None:
        return False

    if start_date and now < start_date:
        return False

    return now < expiration_date


def _require_teacher(teacher_username: Optional[str]) -> str:
    if not teacher_username:
        raise HTTPException(status_code=401, detail="Authentication required")

    teacher = teachers_collection.find_one({"_id": teacher_username})
    if not teacher:
        raise HTTPException(status_code=401, detail="Invalid teacher credentials")

    return teacher["_id"]


def _validate_payload(payload: AnnouncementPayload) -> Dict[str, Optional[str]]:
    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message is required")

    start_date = _parse_iso_datetime(payload.start_date, "start_date")
    expiration_date = _parse_iso_datetime(payload.expiration_date, "expiration_date")

    if expiration_date is None:
        raise HTTPException(status_code=400, detail="Expiration date is required")

    if start_date and expiration_date <= start_date:
        raise HTTPException(status_code=400, detail="Expiration date must be after start date")

    return {
        "message": message,
        "start_date": start_date.isoformat() if start_date else None,
        "expiration_date": expiration_date.isoformat()
    }


@router.get("", response_model=List[Dict[str, Any]])
@router.get("/", response_model=List[Dict[str, Any]])
def get_active_announcements() -> List[Dict[str, Any]]:
    """Get currently active announcements for display in the public banner."""
    announcements = [
        _serialize_announcement(item)
        for item in announcements_collection.find().sort("created_at", -1)
        if _is_active_announcement(item)
    ]

    return announcements


@router.get("/manage", response_model=List[Dict[str, Any]])
def list_announcements_for_management(teacher_username: Optional[str] = Query(None)) -> List[Dict[str, Any]]:
    """List all announcements for authenticated teachers."""
    _require_teacher(teacher_username)

    announcements = [
        _serialize_announcement(item)
        for item in announcements_collection.find().sort("created_at", -1)
    ]

    return announcements


@router.post("", response_model=Dict[str, Any])
def create_announcement(
    payload: AnnouncementPayload,
    teacher_username: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """Create a new announcement. Requires teacher authentication."""
    creator = _require_teacher(teacher_username)
    valid_data = _validate_payload(payload)

    now_iso = datetime.now(timezone.utc).isoformat()
    document = {
        "message": valid_data["message"],
        "start_date": valid_data["start_date"],
        "expiration_date": valid_data["expiration_date"],
        "created_at": now_iso,
        "updated_at": now_iso,
        "created_by": creator
    }

    result = announcements_collection.insert_one(document)
    created = announcements_collection.find_one({"_id": result.inserted_id})

    if not created:
        raise HTTPException(status_code=500, detail="Failed to create announcement")

    return _serialize_announcement(created)


@router.put("/{announcement_id}", response_model=Dict[str, Any])
def update_announcement(
    announcement_id: str,
    payload: AnnouncementPayload,
    teacher_username: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """Update an announcement. Requires teacher authentication."""
    _require_teacher(teacher_username)
    valid_data = _validate_payload(payload)

    try:
        object_id = ObjectId(announcement_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid announcement id") from exc

    result = announcements_collection.update_one(
        {"_id": object_id},
        {
            "$set": {
                "message": valid_data["message"],
                "start_date": valid_data["start_date"],
                "expiration_date": valid_data["expiration_date"],
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Announcement not found")

    updated = announcements_collection.find_one({"_id": object_id})
    if not updated:
        raise HTTPException(status_code=500, detail="Failed to update announcement")

    return _serialize_announcement(updated)


@router.delete("/{announcement_id}", response_model=Dict[str, str])
def delete_announcement(
    announcement_id: str,
    teacher_username: Optional[str] = Query(None)
) -> Dict[str, str]:
    """Delete an announcement. Requires teacher authentication."""
    _require_teacher(teacher_username)

    try:
        object_id = ObjectId(announcement_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid announcement id") from exc

    result = announcements_collection.delete_one({"_id": object_id})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Announcement not found")

    return {"message": "Announcement deleted"}
