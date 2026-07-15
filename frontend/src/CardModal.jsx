import { useState, useEffect } from "react";
import { cardsAPI, commentsAPI, usersAPI } from "./api";
import "./CardModal.css";

const PRIORITY_OPTIONS = [
  { value: "low", label: "Низкий" },
  { value: "medium", label: "Средний" },
  { value: "high", label: "Высокий" },
  { value: "critical", label: "Критический" },
];

function formatDate(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function toDateInputValue(iso) {
  if (!iso) return "";
  return iso.slice(0, 10);
}

export default function CardModal({ card, onClose, onSave, onDelete }) {
  const [title, setTitle] = useState(card.title || "");
  const [description, setDescription] = useState(card.description || "");
  const [priority, setPriority] = useState(card.priority || "medium");
  const [assigneeId, setAssigneeId] = useState(card.assignee_id || "");
  const [deadline, setDeadline] = useState(toDateInputValue(card.deadline));
  const [version, setVersion] = useState(card.version);
  const [users, setUsers] = useState([]);
  const [comments, setComments] = useState([]);
  const [newComment, setNewComment] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [addingComment, setAddingComment] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        const [usersData, commentsData] = await Promise.all([
          usersAPI.getAll(),
          commentsAPI.getByCard(card.id),
        ]);
        setUsers(usersData);
        setComments(commentsData);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [card.id]);

  const handleSave = async () => {
    if (!title.trim()) {
      setError("Название карточки обязательно");
      return;
    }
    try {
      setSaving(true);
      setError("");
      const payload = {
        title: title.trim(),
        description,
        priority,
        assignee_id: assigneeId || null,
        deadline: deadline ? `${deadline}T23:59:59` : null,
        version,
      };
      const response = await cardsAPI.update(card.id, payload);
      const updated = response.card;
      setVersion(updated.version);
      onSave(updated);
      onClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm("Удалить эту карточку?")) return;
    try {
      setSaving(true);
      await cardsAPI.delete(card.id);
      onDelete(card.id);
      onClose();
    } catch (err) {
      setError(err.message);
      setSaving(false);
    }
  };

  const handleAddComment = async () => {
    const content = newComment.trim();
    if (!content) return;
    try {
      setAddingComment(true);
      const response = await commentsAPI.add(card.id, content);
      setComments((prev) => [...prev, response.comment]);
      setNewComment("");
    } catch (err) {
      setError(err.message);
    } finally {
      setAddingComment(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Редактирование карточки</h2>
          <button type="button" className="btn-text" onClick={onClose}>
            Закрыть
          </button>
        </div>

        {error && <div className="modal-error">{error}</div>}

        {loading ? (
          <div className="modal-loading">Загрузка...</div>
        ) : (
          <>
            <div className="modal-body">
              <div className="form-group">
                <label htmlFor="card-title">Название</label>
                <input
                  id="card-title"
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="Название карточки"
                />
              </div>

              <div className="form-group">
                <label htmlFor="card-description">Описание</label>
                <textarea
                  id="card-description"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Описание задачи"
                  rows={4}
                />
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label htmlFor="card-priority">Приоритет</label>
                  <select
                    id="card-priority"
                    value={priority}
                    onChange={(e) => setPriority(e.target.value)}
                  >
                    {PRIORITY_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label htmlFor="card-deadline">Дедлайн</label>
                  <input
                    id="card-deadline"
                    type="date"
                    value={deadline}
                    onChange={(e) => setDeadline(e.target.value)}
                  />
                </div>
              </div>

              <div className="form-group">
                <label htmlFor="card-assignee">Исполнитель</label>
                <select
                  id="card-assignee"
                  value={assigneeId}
                  onChange={(e) => setAssigneeId(e.target.value)}
                >
                  <option value="">Не назначен</option>
                  {users.map((u) => (
                    <option key={u.id} value={u.id}>
                      {u.username}
                    </option>
                  ))}
                </select>
              </div>

              <div className="comments-section">
                <h3>Комментарии</h3>
                {comments.length === 0 ? (
                  <p className="comments-empty">Комментариев пока нет</p>
                ) : (
                  <ul className="comments-list">
                    {comments.map((c) => (
                      <li key={c.id} className="comment-item">
                        <div className="comment-header">
                          <span className="comment-author">{c.author}</span>
                          <span className="comment-date">{formatDate(c.created_at)}</span>
                        </div>
                        <p className="comment-text">{c.content}</p>
                      </li>
                    ))}
                  </ul>
                )}
                <div className="comment-form">
                  <textarea
                    value={newComment}
                    onChange={(e) => setNewComment(e.target.value)}
                    placeholder="Написать комментарий..."
                    rows={2}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !e.shiftKey) {
                        e.preventDefault();
                        handleAddComment();
                      }
                    }}
                  />
                  <button
                    className="btn-primary btn-sm"
                    onClick={handleAddComment}
                    disabled={addingComment || !newComment.trim()}
                  >
                    {addingComment ? "..." : "Добавить комментарий"}
                  </button>
                </div>
              </div>
            </div>

            <div className="modal-footer">
              <button className="btn-danger" onClick={handleDelete} disabled={saving}>
                Удалить карточку
              </button>
              <div className="modal-footer-right">
                <button className="btn-secondary" onClick={onClose} disabled={saving}>
                  Отмена
                </button>
                <button className="btn-primary" onClick={handleSave} disabled={saving || !title.trim()}>
                  {saving ? "Сохранение..." : "Сохранить"}
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
