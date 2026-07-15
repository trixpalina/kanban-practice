from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

# --- Аутентификация ---
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

# --- Доски ---
class BoardCreate(BaseModel):
    title: str
    description: Optional[str] = None
    meeting_room: Optional[str] = None

class BoardUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    meeting_room: Optional[str] = None

# --- Колонки ---
class ColumnCreate(BaseModel):
    title: str
    board_id: str
    position: Optional[int] = None

class ColumnUpdate(BaseModel):
    title: Optional[str] = None
    position: Optional[int] = None

# --- Карточки ---
class CardCreate(BaseModel):
    title: str
    description: Optional[str] = None
    priority: str = "medium"
    deadline: Optional[datetime] = None
    position: Optional[int] = None
    column_id: str
    assignee_id: Optional[str] = None

class CardUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    column_id: Optional[str] = None
    position: Optional[int] = None
    assignee_id: Optional[str] = None
    deadline: Optional[datetime] = None
    version: int

# --- Комментарии ---
class CommentCreate(BaseModel):
    content: str

# --- Участники доски ---
class BoardMemberCreate(BaseModel):
    user_id: str
    role_id: int

class BoardMemberUpdate(BaseModel):
    role_id: int
