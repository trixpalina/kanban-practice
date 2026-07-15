# ER-диаграмма базы данных Kanban-доски

## Описание модели
Модель реализована с использованием реляционной базы данных PostgreSQL. 
Ключевые особенности:
- **RBAC (Role-Based Access Control):** Разделение прав через таблицу `board_members` и `roles`.
- **Audit Log (История изменений):** Таблица `card_history` фиксирует все изменения карточек (требование ТЗ).
- **Защита от коллизий:** Поле `version` в таблице `cards` для оптимистичной блокировки.
- **Безопасность:** Пароли хранятся в виде bcrypt-хэшей.

## Схема базы данных

```mermaid
erDiagram
    USERS ||--o{ BOARD_MEMBERS : "имеет доступ"
    USERS ||--o{ CARDS : "назначен исполнителем"
    USERS ||--o{ COMMENTS : "пишет"
    USERS ||--o{ CARD_HISTORY : "изменяет"
    
    BOARDS ||--o{ BOARD_MEMBERS : "содержит"
    BOARDS ||--o{ COLUMNS : "содержит"
    
    COLUMNS ||--o{ CARDS : "содержит"
    
    CARDS ||--o{ COMMENTS : "имеет"
    CARDS ||--o{ CARD_HISTORY : "отслеживается"
    
    ROLES ||--o{ BOARD_MEMBERS : "определяет"

    USERS {
        uuid id PK
        varchar username UK
        varchar email UK
        varchar hashed_password "Безопасное хранение"
        timestamp created_at
    }
    
    ROLES {
        int id PK
        varchar name UK "owner/writer/reader"
        text description
    }
    
    BOARDS {
        uuid id PK
        varchar title
        text description
        varchar meeting_room "Требование ТЗ"
        uuid owner_id FK
    }
    
    BOARD_MEMBERS {
        uuid board_id PK,FK
        uuid user_id PK,FK
        int role_id FK
    }
    
    COLUMNS {
        uuid id PK
        uuid board_id FK
        varchar title
        int position
    }
    
    CARDS {
        uuid id PK
        uuid column_id FK
        uuid assignee_id FK
        varchar title
        varchar priority "low/medium/high/critical"
        int version "Защита от коллизий"
        timestamp deadline
    }
    
    COMMENTS {
        uuid id PK
        uuid card_id FK
        uuid user_id FK
        text content
    }
    
    CARD_HISTORY {
        uuid id PK
        uuid card_id FK
        uuid user_id FK
        varchar action "moved/edited/created"
        jsonb old_value
        jsonb new_value
        timestamp changed_at
    }
