from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import timedelta

from .database import engine, get_db, SessionLocal
from .models import Base, User, Role, Board, BoardMember, Column, Card, CardHistory, Comment
from .schemas import UserCreate, UserLogin, Token, BoardCreate, BoardUpdate, ColumnCreate, ColumnUpdate, CardCreate, CardUpdate, CommentCreate, BoardMemberCreate, BoardMemberUpdate
from .auth import get_password_hash, verify_password, create_access_token, get_current_user, check_board_role
from .config import settings
import uuid
from datetime import datetime

# Создаем таблицы при запуске (для простоты MVP)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Kanban API", description="API для Kanban-доски с RBAC и защитой от коллизий")

# Настройка CORS (разрешаем фронтенду делать запросы)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Аутентификация ---
@app.post("/api/auth/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter((User.username == user.username) | (User.email == user.email)).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Пользователь уже существует")
    
    new_user = User(
        id=str(uuid.uuid4()),
        username=user.username,
        email=user.email,
        hashed_password=get_password_hash(user.password) # ХЭШИРУЕМ ПАРОЛЬ!
    )
    db.add(new_user)
    
    # Создаем роль "owner" по умолчанию, если её нет
    if not db.query(Role).filter(Role.name == "owner").first():
        db.add_all([
            Role(id=1, name="owner", description="Владелец"),
            Role(id=2, name="writer", description="Редактор"),
            Role(id=3, name="reader", description="Читатель")
        ])
    
    db.commit()
    db.refresh(new_user)
    return {"msg": "Пользователь успешно зарегистрирован"}

@app.post("/api/auth/login", response_model=Token)
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")
    
    # Выдаем JWT токен
    access_token = create_access_token(
        data={"sub": db_user.username},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
    }

# --- Доски ---
@app.post("/api/boards")
def create_board(board: BoardCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    new_board = Board(
        id=str(uuid.uuid4()),
        title=board.title,
        description=board.description,
        meeting_room=board.meeting_room,
        owner_id=current_user.id
    )
    db.add(new_board)
    db.flush()
    
    # Добавляем создателя как владельца (RBAC)
    owner_role = db.query(Role).filter(Role.name == "owner").first()
    db.add(BoardMember(board_id=new_board.id, user_id=current_user.id, role_id=owner_role.id))
    db.commit()
    return {"msg": "Доска создана", "board_id": new_board.id}

# --- Карточки (с защитой от коллизий) ---
def _serialize_card(card: Card, db: Session) -> dict:
    assignee = db.query(User).filter(User.id == card.assignee_id).first() if card.assignee_id else None
    return {
        "id": card.id,
        "title": card.title,
        "description": card.description or "",
        "priority": card.priority,
        "deadline": card.deadline.isoformat() if card.deadline else None,
        "position": card.position,
        "version": card.version,
        "assignee_id": card.assignee_id,
        "assignee": assignee.username if assignee else None,
        "column_id": card.column_id,
    }

@app.get("/api/cards/{card_id}")
def get_card(card_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    card = db.query(Card).filter(Card.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Карточка не найдена")
    return _serialize_card(card, db)

@app.put("/api/cards/{card_id}")
def update_card(
    card_id: str,
    card_update: CardUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    card = db.query(Card).filter(Card.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Карточка не найдена")

    if card.version != card_update.version:
        raise HTTPException(status_code=409, detail="Конфликт версий! Карточка была изменена другим пользователем. Обновите данные.")

    updates = card_update.model_dump(exclude_unset=True)
    updates.pop("version", None)

    for field, value in updates.items():
        setattr(card, field, value)

    card.version += 1
    card.updated_at = datetime.utcnow()

    db.add(CardHistory(
        id=str(uuid.uuid4()),
        card_id=card.id,
        user_id=current_user.id,
        action="updated",
        old_value={"version": card_update.version},
        new_value={"version": card.version},
        changed_at=datetime.utcnow()
    ))

    db.commit()
    db.refresh(card)
    return {"msg": "Карточка обновлена", "new_version": card.version, "card": _serialize_card(card, db)}

@app.delete("/api/cards/{card_id}")
def delete_card(card_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    card = db.query(Card).filter(Card.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Карточка не найдена")
    db.delete(card)
    db.commit()
    return {"msg": "Карточка удалена"}

@app.get("/")
def read_root():
    return {"message": "Kanban API is running! Открой /docs для Swagger UI"}
# --- Колонки ---
@app.post("/api/columns")
def create_column(column: ColumnCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    max_pos = db.query(Column).filter(Column.board_id == column.board_id).count()
    position = column.position if column.position is not None else max_pos + 1
    new_column = Column(
        id=str(uuid.uuid4()),
        board_id=column.board_id,
        title=column.title,
        position=position
    )
    db.add(new_column)
    db.commit()
    db.refresh(new_column)
    return {"msg": "Колонка создана", "column_id": new_column.id, "title": new_column.title, "position": new_column.position}

@app.put("/api/columns/{column_id}")
def update_column(column_id: str, column_update: ColumnUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    column = db.query(Column).filter(Column.id == column_id).first()
    if not column:
        raise HTTPException(status_code=404, detail="Колонка не найдена")
    updates = column_update.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(column, field, value)
    db.commit()
    db.refresh(column)
    return {"msg": "Колонка обновлена", "column": {"id": column.id, "title": column.title, "position": column.position}}

@app.delete("/api/columns/{column_id}")
def delete_column(column_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    column = db.query(Column).filter(Column.id == column_id).first()
    if not column:
        raise HTTPException(status_code=404, detail="Колонка не найдена")
    db.delete(column)
    db.commit()
    return {"msg": "Колонка удалена"}

# --- Карточки ---
@app.post("/api/cards")
def create_card(card: CardCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    max_pos = db.query(Card).filter(Card.column_id == card.column_id).count()
    position = card.position if card.position is not None else max_pos

    new_card = Card(
        id=str(uuid.uuid4()),
        column_id=card.column_id,
        assignee_id=card.assignee_id,
        title=card.title,
        description=card.description or "",
        priority=card.priority,
        deadline=card.deadline,
        position=position,
        version=1
    )
    db.add(new_card)
    db.flush()

    db.add(CardHistory(
        id=str(uuid.uuid4()),
        card_id=new_card.id,
        user_id=current_user.id,
        action="created",
        new_value={"title": new_card.title, "priority": new_card.priority},
        changed_at=datetime.utcnow()
    ))

    db.commit()
    return {"msg": "Карточка создана", "card_id": new_card.id, "version": 1}


# --- Комментарии (legacy endpoint) ---
@app.post("/api/comments")
def create_comment_legacy(card_id: str, content: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    comment = Comment(
        id=str(uuid.uuid4()),
        card_id=card_id,
        user_id=current_user.id,
        content=content
    )
    db.add(comment)
    db.commit()
    return {"msg": "Комментарий добавлен"}

# --- Получить все карточки с деталями (сложный запрос) ---
@app.get("/api/cards/detailed")
def get_detailed_cards(db: Session = Depends(get_db)):
    from app.complex_queries import get_cards_with_assignees_and_comments
    results = get_cards_with_assignees_and_comments(db)
    return [{"card_id": r.card_id, "title": r.card_title, "priority": r.priority, 
             "assignee": r.assignee_name, "column": r.column_name, "comments": r.comments_count} 
            for r in results]
# --- Получить все доски пользователя ---
@app.get("/api/boards")
def get_user_boards(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _get_user_boards(current_user, db)

@app.get("/api/boards/me")
def get_my_boards(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _get_user_boards(current_user, db)

def _get_user_boards(current_user: User, db: Session):
    memberships = db.query(BoardMember).filter(BoardMember.user_id == current_user.id).all()
    board_ids = [m.board_id for m in memberships]
    boards = db.query(Board).filter(Board.id.in_(board_ids)).all()
    return [{
        "id": b.id,
        "title": b.title,
        "description": b.description,
        "meeting_room": b.meeting_room,
        "owner_id": b.owner_id
    } for b in boards]

@app.put("/api/boards/{board_id}")
def update_board(board_id: str, board_update: BoardUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    board = db.query(Board).filter(Board.id == board_id).first()
    if not board:
        raise HTTPException(status_code=404, detail="Доска не найдена")
    updates = board_update.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(board, field, value)
    db.commit()
    db.refresh(board)
    return {
        "msg": "Доска обновлена",
        "board": {
            "id": board.id,
            "title": board.title,
            "description": board.description,
            "meeting_room": board.meeting_room,
            "owner_id": board.owner_id,
        }
    }

@app.delete("/api/boards/{board_id}")
def delete_board(board_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    board = db.query(Board).filter(Board.id == board_id).first()
    if not board:
        raise HTTPException(status_code=404, detail="Доска не найдена")
    db.delete(board)
    db.commit()
    return {"msg": "Доска удалена"}

def _get_board_or_404(board_id: str, db: Session) -> Board:
    board = db.query(Board).filter(Board.id == board_id).first()
    if not board:
        raise HTTPException(status_code=404, detail="Доска не найдена")
    return board

def _require_board_owner(board_id: str, current_user: User, db: Session) -> Board:
    board = _get_board_or_404(board_id, db)
    if board.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Только владелец доски может выполнить это действие")
    return board

def _require_board_member(board_id: str, current_user: User, db: Session):
    membership = db.query(BoardMember).filter(
        BoardMember.board_id == board_id,
        BoardMember.user_id == current_user.id,
    ).first()
    if not membership:
        raise HTTPException(status_code=403, detail="Нет доступа к этой доске")
    return membership

def _serialize_member(membership: BoardMember, db: Session) -> dict:
    user = db.query(User).filter(User.id == membership.user_id).first()
    role = db.query(Role).filter(Role.id == membership.role_id).first()
    return {
        "user_id": membership.user_id,
        "username": user.username if user else "Unknown",
        "email": user.email if user else "",
        "role_id": membership.role_id,
        "role_name": role.name if role else "unknown",
    }

@app.get("/api/boards/{board_id}/members")
def get_board_members(
    board_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_board_member(board_id, current_user, db)
    memberships = db.query(BoardMember).filter(BoardMember.board_id == board_id).all()
    board = _get_board_or_404(board_id, db)
    return {
        "owner_id": board.owner_id,
        "members": [_serialize_member(m, db) for m in memberships],
    }

@app.post("/api/boards/{board_id}/members")
def add_board_member(
    board_id: str,
    data: BoardMemberCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_board_owner(board_id, current_user, db)

    if data.role_id not in (1, 2, 3):
        raise HTTPException(status_code=400, detail="Недопустимая роль")

    user = db.query(User).filter(User.id == data.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    existing = db.query(BoardMember).filter(
        BoardMember.board_id == board_id,
        BoardMember.user_id == data.user_id,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Пользователь уже является участником доски")

    membership = BoardMember(board_id=board_id, user_id=data.user_id, role_id=data.role_id)
    db.add(membership)
    db.commit()
    db.refresh(membership)
    return {"msg": "Участник добавлен", "member": _serialize_member(membership, db)}

@app.put("/api/boards/{board_id}/members/{user_id}")
def update_member_role(
    board_id: str,
    user_id: str,
    data: BoardMemberUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    board = _require_board_owner(board_id, current_user, db)

    if data.role_id not in (1, 2, 3):
        raise HTTPException(status_code=400, detail="Недопустимая роль")

    membership = db.query(BoardMember).filter(
        BoardMember.board_id == board_id,
        BoardMember.user_id == user_id,
    ).first()
    if not membership:
        raise HTTPException(status_code=404, detail="Участник не найден")

    if user_id == board.owner_id and data.role_id != 1:
        raise HTTPException(status_code=400, detail="Нельзя изменить роль владельца доски")

    membership.role_id = data.role_id
    db.commit()
    db.refresh(membership)
    return {"msg": "Роль обновлена", "member": _serialize_member(membership, db)}

@app.delete("/api/boards/{board_id}/members/{user_id}")
def remove_board_member(
    board_id: str,
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    board = _require_board_owner(board_id, current_user, db)

    if user_id == board.owner_id:
        raise HTTPException(status_code=400, detail="Нельзя удалить владельца доски")

    membership = db.query(BoardMember).filter(
        BoardMember.board_id == board_id,
        BoardMember.user_id == user_id,
    ).first()
    if not membership:
        raise HTTPException(status_code=404, detail="Участник не найден")

    db.delete(membership)
    db.commit()
    return {"msg": "Участник удалён"}

# --- Получить колонки доски ---
@app.get("/api/boards/{board_id}/columns")
def get_board_columns(board_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    columns = db.query(Column).filter(Column.board_id == board_id).order_by(Column.position).all()
    return [{"id": c.id, "title": c.title, "position": c.position} for c in columns]

# --- Получить все карточки доски (с группировкой по колонкам) ---
@app.get("/api/boards/{board_id}/cards")
def get_board_cards(board_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Получаем все колонки доски
    columns = db.query(Column).filter(Column.board_id == board_id).order_by(Column.position).all()
    
    result = []
    for col in columns:
        cards = db.query(Card).filter(Card.column_id == col.id).order_by(Card.position).all()
        cards_data = []
        for card in cards:
            assignee = db.query(User).filter(User.id == card.assignee_id).first() if card.assignee_id else None
            cards_data.append({
                "id": card.id,
                "title": card.title,
                "description": card.description,
                "priority": card.priority,
                "deadline": card.deadline.isoformat() if card.deadline else None,
                "position": card.position,
                "version": card.version,
                "assignee_id": card.assignee_id,
                "assignee": assignee.username if assignee else None,
                "column_id": card.column_id
            })
        result.append({
            "column_id": col.id,
            "column_title": col.title,
            "cards": cards_data
        })
    
    return result

# --- Обновить позицию карточки (для drag-and-drop) ---
@app.put("/api/cards/{card_id}/move")
def move_card(
    card_id: str,
    new_column_id: str,
    new_position: int,
    version: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    card = db.query(Card).filter(Card.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Карточка не найдена")
    
    # Защита от коллизий
    if card.version != version:
        raise HTTPException(status_code=409, detail="Конфликт версий! Карточка была изменена.")
    
    old_column_id = card.column_id
    card.column_id = new_column_id
    card.position = new_position
    card.version += 1
    card.updated_at = datetime.utcnow()
    
    # Записываем в историю
    db.add(CardHistory(
        id=str(uuid.uuid4()),
        card_id=card.id,
        user_id=current_user.id,
        action="moved",
        old_value={"column_id": old_column_id, "position": card.position - 1},
        new_value={"column_id": new_column_id, "position": new_position},
        changed_at=datetime.utcnow()
    ))
    
    db.commit()
    return {"msg": "Карточка перемещена", "new_version": card.version}

# --- Добавить комментарий ---
@app.post("/api/cards/{card_id}/comments")
def add_comment(
    card_id: str,
    data: CommentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    card = db.query(Card).filter(Card.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Карточка не найдена")
    comment = Comment(
        id=str(uuid.uuid4()),
        card_id=card_id,
        user_id=current_user.id,
        content=data.content
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return {
        "msg": "Комментарий добавлен",
        "comment": {
            "id": comment.id,
            "content": comment.content,
            "author": current_user.username,
            "created_at": comment.created_at.isoformat(),
        }
    }

# --- Получить комментарии карточки ---
@app.get("/api/cards/{card_id}/comments")
def get_comments(card_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    comments = db.query(Comment).filter(Comment.card_id == card_id).order_by(Comment.created_at).all()
    result = []
    for c in comments:
        user = db.query(User).filter(User.id == c.user_id).first()
        result.append({
            "id": c.id,
            "content": c.content,
            "author": user.username if user else "Unknown",
            "created_at": c.created_at.isoformat()
        })
    return result

@app.delete("/api/comments/{comment_id}")
def delete_comment(comment_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Комментарий не найден")
    db.delete(comment)
    db.commit()
    return {"msg": "Комментарий удален"}
# Получить всех пользователей (для добавления)
@app.get("/api/users/all")
def get_all_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return [{"id": u.id, "username": u.username, "email": u.email} for u in users]