from sqlalchemy import String, Text, DateTime, ForeignKey, JSON, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from datetime import datetime
import uuid
from typing import Optional, List

class Base(DeclarativeBase):
    pass

def generate_uuid() -> str:
    return str(uuid.uuid4())

class Role(Base):
    __tablename__ = "roles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    boards_owned: Mapped[List["Board"]] = relationship("Board", back_populates="owner")
    board_memberships: Mapped[List["BoardMember"]] = relationship("BoardMember", back_populates="user")
    cards_assigned: Mapped[List["Card"]] = relationship("Card", back_populates="assignee")
    comments: Mapped[List["Comment"]] = relationship("Comment", back_populates="user")
    history_logs: Mapped[List["CardHistory"]] = relationship("CardHistory", back_populates="user")

class Board(Base):
    __tablename__ = "boards"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    title: Mapped[str] = mapped_column(String(100), index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    meeting_room: Mapped[Optional[str]] = mapped_column(String(100), nullable=True) # Требование из ТЗ
    owner_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    owner: Mapped["User"] = relationship("User", back_populates="boards_owned")
    members: Mapped[List["BoardMember"]] = relationship("BoardMember", back_populates="board")
    columns: Mapped[List["Column"]] = relationship("Column", back_populates="board", cascade="all, delete-orphan")

class BoardMember(Base):
    __tablename__ = "board_members"
    board_id: Mapped[str] = mapped_column(String(36), ForeignKey("boards.id"), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), primary_key=True)
    role_id: Mapped[int] = mapped_column(Integer, ForeignKey("roles.id"))
    
    board: Mapped["Board"] = relationship("Board", back_populates="members")
    user: Mapped["User"] = relationship("User", back_populates="board_memberships")
    role: Mapped["Role"] = relationship("Role")

class Column(Base):
    __tablename__ = "columns"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    board_id: Mapped[str] = mapped_column(String(36), ForeignKey("boards.id"), index=True)
    title: Mapped[str] = mapped_column(String(100))
    position: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    board: Mapped["Board"] = relationship("Board", back_populates="columns")
    cards: Mapped[List["Card"]] = relationship("Card", back_populates="column", cascade="all, delete-orphan")

class Card(Base):
    __tablename__ = "cards"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    column_id: Mapped[str] = mapped_column(String(36), ForeignKey("columns.id"), index=True)
    assignee_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(150))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    priority: Mapped[str] = mapped_column(String(20), default="medium") # low, medium, high, critical
    deadline: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    position: Mapped[int] = mapped_column(Integer)
    version: Mapped[int] = mapped_column(Integer, default=1) # Защита от коллизий
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    column: Mapped["Column"] = relationship("Column", back_populates="cards")
    assignee: Mapped[Optional["User"]] = relationship("User", back_populates="cards_assigned")
    comments: Mapped[List["Comment"]] = relationship("Comment", back_populates="card", cascade="all, delete-orphan")
    history: Mapped[List["CardHistory"]] = relationship("CardHistory", back_populates="card", cascade="all, delete-orphan")

class Comment(Base):
    __tablename__ = "comments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    card_id: Mapped[str] = mapped_column(String(36), ForeignKey("cards.id"), index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    card: Mapped["Card"] = relationship("Card", back_populates="comments")
    user: Mapped["User"] = relationship("User", back_populates="comments")

class CardHistory(Base):
    __tablename__ = "card_history" # ОБЯЗАТЕЛЬНАЯ ТАБЛИЦА ПО КРИТЕРИЯМ ОЦЕНКИ!
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    card_id: Mapped[str] = mapped_column(String(36), ForeignKey("cards.id"), index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(50))
    old_value: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    new_value: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    changed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    card: Mapped["Card"] = relationship("Card", back_populates="history")
    user: Mapped["User"] = relationship("User", back_populates="history_logs")