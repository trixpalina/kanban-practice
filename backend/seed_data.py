import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import sessionmaker
import bcrypt
from datetime import datetime, timedelta
import uuid

from app.database import engine, SessionLocal
from app.models import Base, Role, User, Board, BoardMember, Column, Card, Comment, CardHistory

def seed_database():
    print("📦 Создание таблиц и наполнение тестовыми данными...")
    
    # Создаем все таблицы
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # 1. Роли
        print("  → Создание ролей...")
        roles = [
            Role(id=1, name="owner", description="Владелец доски"),
            Role(id=2, name="writer", description="Редактор"),
            Role(id=3, name="reader", description="Только чтение")
        ]
        for role in roles:
            if not db.query(Role).filter(Role.id == role.id).first():
                db.add(role)
        db.commit()
        
        # 2. Пользователи
        print("  → Создание пользователей...")
        users_data = [
            {"username": "admin", "email": "admin@kanban.com", "password": "admin123"},
            {"username": "ivan", "email": "ivan@kanban.com", "password": "password123"},
            {"username": "maria", "email": "maria@kanban.com", "password": "qwerty123"}
        ]
        
        users = []
        for user_data in users_data:
            existing = db.query(User).filter(User.username == user_data["username"]).first()
            if existing:
                users.append(existing)
            else:
                user = User(
                    id=str(uuid.uuid4()),
                    username=user_data["username"],
                    email=user_data["email"],
                    hashed_password=bcrypt.hashpw(user_data["password"].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                )
                db.add(user)
                db.flush()
                users.append(user)
        
        # 3. Доска
        print("  → Создание доски...")
        board = Board(
            id=str(uuid.uuid4()),
            title="Разработка сайта",
            description="Доска для отслеживания задач по проекту",
            meeting_room="Переговорная №3",  # Требование из ТЗ!
            owner_id=users[0].id
        )
        db.add(board)
        db.flush()
        
        # 4. Участники доски (RBAC)
        db.add(BoardMember(board_id=board.id, user_id=users[0].id, role_id=1))  # Владелец
        db.add(BoardMember(board_id=board.id, user_id=users[1].id, role_id=2))  # Редактор
        db.add(BoardMember(board_id=board.id, user_id=users[2].id, role_id=3))  # Читатель
        
        # 5. Колонки
        print("  → Создание колонок...")
        col1 = Column(id=str(uuid.uuid4()), board_id=board.id, title="Нужно сделать", position=1)
        col2 = Column(id=str(uuid.uuid4()), board_id=board.id, title="В работе", position=2)
        col3 = Column(id=str(uuid.uuid4()), board_id=board.id, title="Готово", position=3)
        db.add_all([col1, col2, col3])
        db.flush()
        
        # 6. Карточки с ПРИОРИТЕТАМИ
        print("  → Создание карточек...")
        cards_data = [
            {"column": col1, "assignee": users[1], "title": "Сверстать главную", "priority": "high", "days": 2},
            {"column": col1, "assignee": None, "title": "Настроить БД", "priority": "critical", "days": 1},
            {"column": col2, "assignee": users[2], "title": "Написать API", "priority": "medium", "days": 5},
            {"column": col3, "assignee": users[0], "title": "Создать репозиторий", "priority": "low", "days": -1}
        ]
        
        cards = []
        for i, data in enumerate(cards_data):
            card = Card(
                id=str(uuid.uuid4()),
                column_id=data["column"].id,
                assignee_id=data["assignee"].id if data["assignee"] else None,
                title=data["title"],
                description=f"Описание задачи {i+1}",
                priority=data["priority"],
                deadline=datetime.utcnow() + timedelta(days=data["days"]),
                position=i+1,
                version=1
            )
            db.add(card)
            db.flush()
            cards.append(card)
            
            # История изменений (ОБЯЗАТЕЛЬНО ПО ТЗ!)
            db.add(CardHistory(
                id=str(uuid.uuid4()),
                card_id=card.id,
                user_id=users[0].id,
                action="created",
                new_value={"title": card.title, "priority": card.priority},
                changed_at=datetime.utcnow()
            ))
        
        # 7. Комментарии
        print("  → Добавление комментариев...")
        db.add(Comment(
            id=str(uuid.uuid4()),
            card_id=cards[0].id,
            user_id=users[1].id,
            content="Начинаю верстку сегодня."
        ))
        
        db.commit()
        print("✅ База данных успешно наполнена!")
        print("\n Тестовые данные:")
        print("  Пользователи:")
        for u in users:
            print(f"    - {u.username} ({u.email}) / пароль: admin123, password123, qwerty123")
        print(f"  Доска: {board.title}")
        print(f"  Колонки: 3")
        print(f"  Карточки: {len(cards)}")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Ошибка: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
