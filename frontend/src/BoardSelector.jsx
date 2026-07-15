import { useState, useEffect, useRef } from "react";
import { boardsAPI } from "./api";
import "./CardModal.css";

export default function BoardSelector({ currentBoard, onSelectBoard, onBoardUpdated, onBoardDeleted }) {
  const [open, setOpen] = useState(false);
  const [boards, setBoards] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showEdit, setShowEdit] = useState(false);
  const [editTitle, setEditTitle] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [editMeetingRoom, setEditMeetingRoom] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const dropdownRef = useRef(null);

  const loadBoards = async () => {
    try {
      setLoading(true);
      const data = await boardsAPI.getMe();
      setBoards(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (open) loadBoards();
  }, [open]);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const openEdit = () => {
    if (!currentBoard) return;
    setEditTitle(currentBoard.title || "");
    setEditDescription(currentBoard.description || "");
    setEditMeetingRoom(currentBoard.meeting_room || "");
    setShowEdit(true);
    setOpen(false);
  };

  const handleSaveBoard = async () => {
    if (!editTitle.trim()) {
      setError("Название доски обязательно");
      return;
    }
    try {
      setSaving(true);
      setError("");
      const response = await boardsAPI.update(currentBoard.id, {
        title: editTitle.trim(),
        description: editDescription,
        meeting_room: editMeetingRoom,
      });
      onBoardUpdated(response.board);
      setShowEdit(false);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteBoard = async () => {
    if (!window.confirm(`Удалить доску "${currentBoard.title}"?`)) return;
    try {
      setSaving(true);
      await boardsAPI.delete(currentBoard.id);
      setShowEdit(false);
      onBoardDeleted(currentBoard.id);
    } catch (err) {
      setError(err.message);
      setSaving(false);
    }
  };

  const handleCreateBoard = async () => {
    try {
      setSaving(true);
      setError("");
      const response = await boardsAPI.create("Новая доска");
      const data = await boardsAPI.getMe();
      setBoards(data);
      const newBoard = data.find((b) => b.id === response.board_id) || {
        id: response.board_id,
        title: "Новая доска",
        description: "",
        meeting_room: "",
      };
      onSelectBoard(newBoard);
      setOpen(false);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <div className="board-selector" ref={dropdownRef}>
        <button className="btn-secondary btn-sm" onClick={() => setOpen(!open)}>
          Мои доски
        </button>
        {open && (
          <div className="board-dropdown">
            {loading ? (
              <div className="board-dropdown-loading">Загрузка...</div>
            ) : (
              <>
                {boards.map((b) => (
                  <button
                    key={b.id}
                    className={`board-dropdown-item ${b.id === currentBoard?.id ? "active" : ""}`}
                    onClick={() => {
                      onSelectBoard(b);
                      setOpen(false);
                    }}
                  >
                    <span className="board-dropdown-title">{b.title}</span>
                    {b.meeting_room && (
                      <span className="board-dropdown-meta">{b.meeting_room}</span>
                    )}
                  </button>
                ))}
                <div className="board-dropdown-divider" />
                <button className="board-dropdown-item create" onClick={handleCreateBoard} disabled={saving}>
                  + Создать доску
                </button>
              </>
            )}
          </div>
        )}
      </div>

      <button className="btn-secondary btn-sm" onClick={openEdit} disabled={!currentBoard}>
        Редактировать доску
      </button>

      {showEdit && (
        <div className="modal-overlay" onClick={() => setShowEdit(false)}>
          <div className="modal-content board-edit-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Редактирование доски</h2>
              <button type="button" className="btn-text" onClick={() => setShowEdit(false)}>
                Закрыть
              </button>
            </div>
            {error && <div className="modal-error">{error}</div>}
            <div className="modal-body">
              <div className="form-group">
                <label htmlFor="board-title">Название</label>
                <input
                  id="board-title"
                  type="text"
                  value={editTitle}
                  onChange={(e) => setEditTitle(e.target.value)}
                />
              </div>
              <div className="form-group">
                <label htmlFor="board-description">Описание</label>
                <textarea
                  id="board-description"
                  value={editDescription}
                  onChange={(e) => setEditDescription(e.target.value)}
                  rows={3}
                />
              </div>
              <div className="form-group">
                <label htmlFor="board-room">Переговорная</label>
                <input
                  id="board-room"
                  type="text"
                  value={editMeetingRoom}
                  onChange={(e) => setEditMeetingRoom(e.target.value)}
                />
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn-danger" onClick={handleDeleteBoard} disabled={saving}>
                Удалить доску
              </button>
              <div className="modal-footer-right">
                <button className="btn-secondary" onClick={() => setShowEdit(false)} disabled={saving}>
                  Отмена
                </button>
                <button className="btn-primary" onClick={handleSaveBoard} disabled={saving || !editTitle.trim()}>
                  {saving ? "Сохранение..." : "Сохранить"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
