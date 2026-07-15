import { useState } from "react";
import { columnsAPI } from "./api";

export default function ColumnManager({ boardId, onColumnCreated, onColumnDeleted }) {
  const [showForm, setShowForm] = useState(false);
  const [title, setTitle] = useState("");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");

  const handleCreate = async () => {
    const trimmed = title.trim();
    if (!trimmed) return;
    try {
      setCreating(true);
      setError("");
      const response = await columnsAPI.create(boardId, trimmed);
      onColumnCreated({
        id: String(response.column_id),
        title: response.title || trimmed,
        cardIds: [],
      });
      setTitle("");
      setShowForm(false);
    } catch (err) {
      setError(err.message);
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="column-manager">
      {showForm ? (
        <div className="add-column-form">
          <input
            type="text"
            placeholder="Название колонки"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleCreate();
              if (e.key === "Escape") {
                setShowForm(false);
                setTitle("");
              }
            }}
            autoFocus
          />
          {error && <div className="inline-error">{error}</div>}
          <div className="add-column-actions">
            <button
              className="btn-primary btn-sm"
              onClick={handleCreate}
              disabled={creating || !title.trim()}
            >
              {creating ? "..." : "Создать"}
            </button>
            <button
              className="btn-secondary btn-sm"
              onClick={() => {
                setShowForm(false);
                setTitle("");
                setError("");
              }}
            >
              Отмена
            </button>
          </div>
        </div>
      ) : (
        <button className="add-column-btn" onClick={() => setShowForm(true)}>
          + Добавить колонку
        </button>
      )}
    </div>
  );
}

export function ColumnHeader({ column, onDelete, onRename }) {
  const [editing, setEditing] = useState(false);
  const [title, setTitle] = useState(column.title);

  const handleRename = async () => {
    const trimmed = title.trim();
    if (!trimmed || trimmed === column.title) {
      setEditing(false);
      setTitle(column.title);
      return;
    }
    try {
      await onRename(column.id, trimmed);
      setEditing(false);
    } catch {
      setTitle(column.title);
      setEditing(false);
    }
  };

  const handleDelete = () => {
    if (window.confirm(`Удалить колонку "${column.title}"? Все карточки в ней будут удалены.`)) {
      onDelete(column.id);
    }
  };

  return (
    <div className="column-title">
      {editing ? (
        <input
          className="column-rename-input"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          onBlur={handleRename}
          onKeyDown={(e) => {
            if (e.key === "Enter") handleRename();
            if (e.key === "Escape") {
              setTitle(column.title);
              setEditing(false);
            }
          }}
          autoFocus
        />
      ) : (
        <span className="column-title-text" onDoubleClick={() => setEditing(true)}>
          {column.title}
        </span>
      )}
      <div className="column-title-actions">
        <span className="column-count">{column.cardIds?.length || 0}</span>
        <button type="button" className="column-delete-btn" onClick={handleDelete} title="Удалить колонку">
          Удалить
        </button>
      </div>
    </div>
  );
}
