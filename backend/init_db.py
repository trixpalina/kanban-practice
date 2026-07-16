import sys
import os
# Добавляем папку app в путь, чтобы импорты работали
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import sessionmaker
from passlib.hash import bcrypt
from datetime import datetime, timedelta
import uuid

from app.database import engine
from app.models import Base, Role, User, Board, BoardMember, Column, Card, Comment, CardHistory

# Создаем сессию
SessionLocal = sessionmaker(bind=engine)

def seed_database():
    # 1. Создаем все таблицы в БД
    print("Создание таблиц...")
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # 2. Создаем роли (RBAC)
        print("Наполнение ролей...")
        roles_data = [
            {"id": 1, "name": "owner", "description": "Владелец доски"},
            {"id": 2, "name": "writer", "description": "Редактор"},
            {"id": 3, "name": "reader", "description": "Только чтение"}
        ]
        for role_data in roles_data:
            if not db.query(Role).filter(Role.id == role_data["id"]).first():
                db.add(Role(**role_data))
        
        # 3. Создаем пользователей (с БЕЗОПАСНЫМ хэшированием паролей!)
        print("Создание пользователей...")
        users_data = [
            {"id": str(uuid.uuid4()), "username": "admin", "email": "admin@kanban.com", "hashed_password": bcrypt.hash("admin123")},
            {"id": str(uuid.uuid4()), "username": "ivan", "email": "ivan@kanban.com", "hashed_password": bcrypt.hash("password123")},
            {"id": str(uuid.uuid4()), "username": "maria", "email": "maria@kanban.com", "hashed_password": bcrypt.hash("qwerty123")}
        ]
        created_users = []
        for user_data in users_data:
            if not db.query(User).filter(User.username == user_data["username"]).first():
                user = User(**user_data)
                db.add(user)
                db.flush() # Чтобы получить ID пользователя
                created_users.append(user)
        
        if not created_users:
            created_users = db.query(User).all()

        # 4. Создаем доску
        print("Создание доски...")
        board = Board(
            id=str(uuid.uuid4()),
            title="Разработка сайта",
            description="Доска для отслеживания задач по проекту",
            meeting_room="Переговорная №3", # Требование из PDF про "комнаты"
            owner_id=created_users[0].id
        )
        db.add(board)
        db.flush()

        # 5. Добавляем участников доски (RBAC)
        db.add(BoardMember(board_id=board.id, user_id=created_users[0].id, role_id=1)) # Владелец
        db.add(BoardMember(board_id=board.id, user_id=created_users[1].id, role_id=2)) # Редактор
        db.add(BoardMember(board_id=board.id, user_id=created_users[2].id, role_id=3)) # Читатель

        # 6. Создаем колонки
        print("Создание колонок...")
        col1 = Column(id=str(uuid.uuid4()), board_id=board.id, title="Нужно сделать", position=1)
        col2 = Column(id=str(uuid.uuid4()), board_id=board.id, title="В работе", position=2)
        col3 = Column(id=str(uuid.uuid4()), board_id=board.id, title="Готово", position=3)
        db.add_all([col1, col2, col3])
        db.flush()

        # 7. Создаем карточки с ПРИОРИТЕТАМИ и ЗАЩИТОЙ ОТ КОЛЛИЗИЙ (version)
        print("Создание карточек...")
        cards_data = [
            {"column_id": col1.id, "assignee_id": created_users[1].id, "title": "Сверстать главную", "priority": "high", "deadline": datetime.utcnow() + timedelta(days=2), "position": 1, "version": 1},
            {"column_id": col1.id, "assignee_id": None, "title": "Настроить БД", "priority": "critical", "deadline": datetime.utcnow() + timedelta(days=1), "position": 2, "version": 1},
            {"column_id": col2.id, "assignee_id": created_users[2].id, "title": "Написать API", "priority": "medium", "deadline": datetime.utcnow() + timedelta(days=5), "position": 1, "version": 1},
            {"column_id": col3.id, "assignee_id": created_users[0].id, "title": "Создать репозиторий", "priority": "low", "deadline": datetime.utcnow() - timedelta(days=1), "position": 1, "version": 2} # version=2, т.к. уже меняли
        ]
        created_cards = []
        for card_data in cards_data:
            card = Card(**card_data)
            db.add(card)
            db.flush()
            created_cards.append(card)
            
            # 8. Создаем ИСТОРИЮ ИЗМЕНЕНИЙ (Audit Log) - ОБЯЗАТЕЛЬНО ПО КРИТЕРИЯМ!
            db.add(CardHistory(
                id=str(uuid.uuid4()),
                card_id=card.id,
                user_id=created_users[0].id,
                action="created",
                new_value={"title": card.title, "priority": card.priority},
                changed_at=datetime.utcnow()
            ))

        # 9. Добавляем комментарии
        db.add(Comment(id=str(uuid.uuid4()), card_id=created_cards[0].id, user_id=created_users[1].id, content="Начинаю верстку сегодня."))
        
        db.commit()
        print(" База данных успешно создана и наполнена тестовыми данными!")
        
    except Exception as e:
        db.rollback()
        print(f" Ошибка при наполнении БД: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
