from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional

# User Schemas
class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str # Will be hashed before storing

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class User(UserBase):
    id: int

    class Config:
        from_attributes = True # Replaces orm_mode = True in Pydantic v2

# Email Schemas
class EmailBase(BaseModel):
    subject: Optional[str] = "No Subject"
    body: str

class EmailCreate(EmailBase):
    receiver_email: EmailStr

class Email(EmailBase):
    id: int
    sender_id: int
    receiver_id: int
    timestamp: datetime
    is_read: bool
    is_spam: bool
    sender: User # To show sender details
    receiver: User # To show receiver details

    class Config:
        from_attributes = True # Replaces orm_mode = True in Pydantic v2

class EmailSent(EmailBase):
    id: int
    receiver_email: EmailStr
    timestamp: datetime

    class Config:
        from_attributes = True

class EmailReceived(EmailBase):
    id: int
    sender_email: EmailStr
    timestamp: datetime
    is_read: bool

    class Config:
        from_attributes = True