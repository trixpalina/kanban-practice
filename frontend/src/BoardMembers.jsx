import { useState, useEffect } from "react";
import { membersAPI, usersAPI } from "./api";
import "./BoardMembers.css";

export default function BoardMembers({ board, currentUserId, onClose }) {
  const [members, setMembers] = useState([]);
  const [ownerId, setOwnerId] = useState(null);
  const [allUsers, setAllUsers] = useState([]);
  const [showAddForm, setShowAddForm] = useState(false);
  const [selectedUser, setSelectedUser] = useState("");
  const [selectedRole, setSelectedRole] = useState("3");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    loadData();
  }, [board?.id]);

  const loadData = async () => {
    try {
      setLoading(true);
      setError("");
      const [membersData, usersData] = await Promise.all([
        membersAPI.getByBoard(board.id),
        usersAPI.getAll(),
      ]);
      // Backend возвращает { owner_id, members: [...] }
      if (membersData && Array.isArray(membersData.members)) {
        setMembers(membersData.members);
        setOwnerId(membersData.owner_id);
      } else if (Array.isArray(membersData)) {
        // На случай если вернётся просто массив
        setMembers(membersData);
      } else {
        setMembers([]);
      }
      setAllUsers(usersData || []);
    } catch (err) {
      console.error("Ошибка загрузки:", err);
      setError(err.message || "Не удалось загрузить участников");
      setMembers([]);
    } finally {
      setLoading(false);
    }
  };

  const handleAddMember = async (e) => {
    e.preventDefault();
    try {
      await membersAPI.add(board.id, selectedUser, parseInt(selectedRole));
      setShowAddForm(false);
      setSelectedUser("");
      loadData();
    } catch (err) {
      alert("Ошибка: " + err.message);
    }
  };

  const handleRemoveMember = async (userId) => {
    if (!confirm("Удалить участника?")) return;
    try {
      await membersAPI.remove(board.id, userId);
      loadData();
    } catch (err) {
      alert("Ошибка: " + err.message);
    }
  };

  const handleRoleChange = async (userId, newRoleId) => {
    try {
      await membersAPI.updateRole(board.id, userId, parseInt(newRoleId));
      loadData();
    } catch (err) {
      alert("Ошибка: " + err.message);
    }
  };

  const getRoleName = (roleId) => {
    const roles = { 1: "Владелец", 2: "Редактор", 3: "Читатель" };
    return roles[roleId] || "Неизвестно";
  };

  // Проверяем, является ли текущий пользователь владельцем (сравниваем username)
const isOwner = currentUserId && members.some(m => m.username === currentUserId && m.role_id === 1);
  if (loading) {
    return (
      <div className="modal-overlay" onClick={onClose}>
        <div className="modal-content" onClick={(e) => e.stopPropagation()}>
          <p>Загрузка...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Участники доски</h2>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>

        {error && <div className="error-banner">{error}</div>}

        <div className="members-list">
          {members.map((member) => (
            <div key={member.user_id} className="member-item">
              <div className="member-info">
                <strong>{member.username}</strong>
                <span className="member-email">{member.email}</span>
              </div>
              <div className="member-actions">
                {isOwner && member.user_id !== currentUserId ? (
                  <>
                    <select
                      value={member.role_id}
                      onChange={(e) => handleRoleChange(member.user_id, e.target.value)}
                      className="role-select"
                    >
                      <option value={1}>Владелец</option>
                      <option value={2}>Редактор</option>
                      <option value={3}>Читатель</option>
                    </select>
                    <button
                      onClick={() => handleRemoveMember(member.user_id)}
                      className="remove-btn"
                    >
                      Удалить
                    </button>
                  </>
                ) : (
                  <span className="role-badge">{getRoleName(member.role_id)}</span>
                )}
              </div>
            </div>
          ))}
        </div>

        {isOwner && (
          <div className="add-member-section">
            {!showAddForm ? (
              <button onClick={() => setShowAddForm(true)} className="add-btn">
                + Добавить участника
              </button>
            ) : (
              <form onSubmit={handleAddMember} className="add-member-form">
                <select
                  value={selectedUser}
                  onChange={(e) => setSelectedUser(e.target.value)}
                  required
                >
                  <option value="">Выберите пользователя</option>
                  {allUsers
                    .filter(u => !members.find(m => m.user_id === u.id))
                    .map(user => (
                      <option key={user.id} value={user.id}>
                        {user.username} ({user.email})
                      </option>
                    ))}
                </select>
                
                <select
                  value={selectedRole}
                  onChange={(e) => setSelectedRole(e.target.value)}
                >
                  <option value={3}>Читатель</option>
                  <option value={2}>Редактор</option>
                  <option value={1}>Владелец</option>
                </select>
                
                <div className="form-actions">
                  <button type="submit" className="save-btn">Добавить</button>
                  <button type="button" onClick={() => setShowAddForm(false)} className="cancel-btn">
                    Отмена
                  </button>
                </div>
              </form>
            )}
          </div>
        )}
      </div>
    </div>
  );
}