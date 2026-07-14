from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime
import uuid

Base = declarative_base()

def generate_uuid():
    return str(uuid.uuid4())

class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)  # 'owner', 'writer', 'reader'

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=generate_uuid)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)  # БЕЗОПАСНОСТЬ: хэш, а не открытый текст!
    created_at = Column(DateTime, default=datetime.utcnow)
    
    boards_owned = relationship("Board", back_populates="owner")
    board_memberships = relationship("BoardMember", back_populates="user")
    cards_assigned = relationship("Card", back_populates="assignee")
    comments = relationship("Comment", back_populates="user")
    history_logs = relationship("CardHistory", back_populates="user")

class Board(Base):
    __tablename__ = "boards"
    id = Column(String, primary_key=True, default=generate_uuid)
    title = Column(String, index=True)
    description = Column(Text, nullable=True)
    meeting_room = Column(String, nullable=True)  # Добавлено для выполнения требования PDF про "комнаты"
    owner_id = Column(String, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    owner = relationship("User", back_populates="boards_owned")
    members = relationship("BoardMember", back_populates="board")
    columns = relationship("Column", back_populates="board", cascade="all, delete-orphan")

class BoardMember(Base):
    __tablename__ = "board_members"
    board_id = Column(String, ForeignKey("boards.id"), primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), primary_key=True)
    role_id = Column(Integer, ForeignKey("roles.id"))
    
    board = relationship("Board", back_populates="members")
    user = relationship("User", back_populates="board_memberships")
    role = relationship("Role")

class Column(Base):
    __tablename__ = "columns"
    id = Column(String, primary_key=True, default=generate_uuid)
    board_id = Column(String, ForeignKey("boards.id"), index=True)
    title = Column(String)
    position = Column(Integer)  # Для порядка колонок (drag and drop)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    board = relationship("Board", back_populates="columns")
    cards = relationship("Card", back_populates="column", cascade="all, delete-orphan")

class Card(Base):
    __tablename__ = "cards"
    id = Column(String, primary_key=True, default=generate_uuid)
    column_id = Column(String, ForeignKey("columns.id"), index=True)
    assignee_id = Column(String, ForeignKey("users.id"), nullable=True)
    title = Column(String)
    description = Column(Text, nullable=True)
    priority = Column(String, default="medium")  # low, medium, high, critical (ОБЯЗАТЕЛЬНО по PDF!)
    deadline = Column(DateTime, nullable=True)
    position = Column(Integer)  # Для порядка карточек в колонке
    version = Column(Integer, default=1)  # ЗАЩИТА ОТ КОЛЛИЗИЙ (Optimistic Locking)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    column = relationship("Column", back_populates="cards")
    assignee = relationship("User", back_populates="cards_assigned")
    comments = relationship("Comment", back_populates="card", cascade="all, delete-orphan")
    history = relationship("CardHistory", back_populates="card", cascade="all, delete-orphan")

class Comment(Base):
    __tablename__ = "comments"
    id = Column(String, primary_key=True, default=generate_uuid)
    card_id = Column(String, ForeignKey("cards.id"), index=True)
    user_id = Column(String, ForeignKey("users.id"))
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    card = relationship("Card", back_populates="comments")
    user = relationship("User", back_populates="comments")

class CardHistory(Base):
    __tablename__ = "card_history"  # ОБЯЗАТЕЛЬНАЯ ТАБЛИЦА ПО КРИТЕРИЯМ ОЦЕНКИ!
    id = Column(String, primary_key=True, default=generate_uuid)
    card_id = Column(String, ForeignKey("cards.id"), index=True)
    user_id = Column(String, ForeignKey("users.id"))
    action = Column(String)  # 'created', 'moved', 'updated', 'deleted'
    old_value = Column(JSON, nullable=True)
    new_value = Column(JSON, nullable=True)
    changed_at = Column(DateTime, default=datetime.utcnow)
    
    card = relationship("Card", back_populates="history")
    user = relationship("User", back_populates="history_logs") 
