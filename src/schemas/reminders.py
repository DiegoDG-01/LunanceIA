from typing import Optional
from datetime import date, datetime
from pydantic import BaseModel, ConfigDict

from utils.enums import ReminderType


class BaseReminder(BaseModel):
    title: str
    description: Optional[str] = None
    reminder_date: date
    type: ReminderType = ReminderType.OTRO
    is_completed: bool = False


class CreateReminder(BaseReminder):
    pass


class UpdateReminder(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    reminder_date: Optional[date] = None
    type: Optional[ReminderType] = None
    is_completed: Optional[bool] = None


class Reminder(BaseReminder):
    reminder_id: int
    user_id: int
    creation_date: datetime

    model_config = ConfigDict(from_attributes=True)