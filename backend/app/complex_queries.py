from sqlalchemy import text
from sqlalchemy.orm import Session

def get_cards_with_assignees_and_comments(db: Session):
    """
    СЛОЖНЫЙ ЗАПРОС 1: JOIN нескольких таблиц
    Возвращает все карточки с именами исполнителей и количеством комментариев
    """
    query = text("""
        SELECT 
            c.id as card_id,
            c.title as card_title,
            c.priority,
            c.deadline,
            u.username as assignee_name,
            col.title as column_name,
            COUNT(DISTINCT cm.id) as comments_count
        FROM cards c
        LEFT JOIN users u ON c.assignee_id = u.id
        LEFT JOIN columns col ON c.column_id = col.id
        LEFT JOIN comments cm ON c.id = cm.card_id
        GROUP BY c.id, c.title, c.priority, c.deadline, u.username, col.title
        ORDER BY c.priority DESC, c.deadline ASC
    """)
    return db.execute(query).fetchall()

def get_board_statistics(db: Session, board_id: str):
    """
    СЛОЖНЫЙ ЗАПРОС 2: GROUP BY с агрегатными функциями
    Возвращает статистику по доске: сколько карточек в каждой колонке
    """
    query = text("""
        SELECT 
            col.title as column_name,
            COUNT(c.id) as cards_count,
            COUNT(CASE WHEN c.priority = 'critical' THEN 1 END) as critical_count,
            COUNT(CASE WHEN c.priority = 'high' THEN 1 END) as high_count,
            AVG(EXTRACT(EPOCH FROM (c.deadline - NOW()))/86400) as avg_days_to_deadline
        FROM columns col
        LEFT JOIN cards c ON col.id = c.column_id
        WHERE col.board_id = :board_id
        GROUP BY col.id, col.title
        ORDER BY col.position
    """)
    return db.execute(query, {"board_id": board_id}).fetchall()

def get_active_users_with_activity(db: Session):
    """
    СЛОЖНЫЙ ЗАПРОС 3: Подзапрос и работа с историей изменений
    Возвращает пользователей и их активность (последние действия)
    """
    query = text("""
        SELECT 
            u.username,
            u.email,
            COUNT(DISTINCT c.id) as cards_created,
            COUNT(DISTINCT cm.id) as comments_written,
            COUNT(DISTINCT ch.id) as actions_in_history,
            (SELECT MAX(ch2.changed_at) 
             FROM card_history ch2 
             WHERE ch2.user_id = u.id) as last_activity
        FROM users u
        LEFT JOIN cards c ON u.id = c.assignee_id
        LEFT JOIN comments cm ON u.id = cm.user_id
        LEFT JOIN card_history ch ON u.id = ch.user_id
        GROUP BY u.id, u.username, u.email
        HAVING COUNT(DISTINCT ch.id) > 0
        ORDER BY last_activity DESC
    """)
    return db.execute(query).fetchall()

def get_overdue_cards_with_details(db: Session):
    """
    СЛОЖНЫЙ ЗАПРОС 4: Фильтрация с несколькими условиями
    Возвращает просроченные карточки с деталями
    """
    query = text("""
        SELECT 
            c.id,
            c.title,
            c.deadline,
            c.priority,
            u.username as assignee,
            b.title as board_name,
            col.title as column_name,
            EXTRACT(DAY FROM (NOW() - c.deadline)) as days_overdue
        FROM cards c
        JOIN columns col ON c.column_id = col.id
        JOIN boards b ON col.board_id = b.id
        LEFT JOIN users u ON c.assignee_id = u.id
        WHERE c.deadline < NOW() 
            AND c.priority IN ('high', 'critical')
        ORDER BY days_overdue DESC, c.priority DESC
    """)
    return db.execute(query).fetchall()

def get_user_role_on_board(db: Session, user_id: str, board_id: str):
    """
    СЛОЖНЫЙ ЗАПРОС 5: Проверка прав доступа (RBAC)
    Возвращает роль пользователя на конкретной доске
    """
    query = text("""
        SELECT 
            r.name as role_name,
            r.description,
            bm.joined_at
        FROM board_members bm
        JOIN roles r ON bm.role_id = r.id
        WHERE bm.user_id = :user_id 
            AND bm.board_id = :board_id
    """)
    return db.execute(query, {"user_id": user_id, "board_id": board_id}).first()
