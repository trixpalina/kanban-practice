const API_URL = "http://127.0.0.1:8001";

const getToken = () => localStorage.getItem("token");

async function request(endpoint, options = {}) {
  const token = getToken();
  const headers = {
    "Content-Type": "application/json",
    ...options.headers,
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (response.status === 401 && !endpoint.startsWith("/api/auth/")) {
    localStorage.removeItem("token");
    window.location.href = "/login";
    throw new Error("Сессия истекла. Войдите снова.");
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Ошибка сервера" }));
    let message = "Ошибка запроса";
    if (typeof error.detail === "string") {
      message = error.detail;
    } else if (Array.isArray(error.detail)) {
      message = error.detail.map((e) => e.msg).join(", ");
    }
    throw new Error(message);
  }

  if (response.status === 204) return null;
  return response.json();
}

export const authAPI = {
  register: (username, email, password) =>
    request("/api/auth/register", {
      method: "POST",
      body: JSON.stringify({ username, email, password }),
    }),

  login: (username, password) =>
    request("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),

  me: () => request("/api/me"),
};

export const boardsAPI = {
  getAll: () => request("/api/boards"),
  getMe: () => request("/api/boards/me"),
  create: (title, description = "", meeting_room = "") =>
    request("/api/boards", {
      method: "POST",
      body: JSON.stringify({ title, description, meeting_room }),
    }),
  update: (boardId, data) =>
    request(`/api/boards/${boardId}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  delete: (boardId) =>
    request(`/api/boards/${boardId}`, { method: "DELETE" }),
};

export const membersAPI = {
  getByBoard: (boardId) => request(`/api/boards/${boardId}/members`),
  add: (boardId, userId, roleId) =>
    request(`/api/boards/${boardId}/members`, {
      method: "POST",
      body: JSON.stringify({ user_id: userId, role_id: roleId }),
    }),
  updateRole: (boardId, userId, roleId) =>
    request(`/api/boards/${boardId}/members/${userId}`, {
      method: "PUT",
      body: JSON.stringify({ role_id: roleId }),
    }),
  remove: (boardId, userId) =>
    request(`/api/boards/${boardId}/members/${userId}`, { method: "DELETE" }),
};

export const columnsAPI = {
  create: (boardId, title) =>
    request("/api/columns", {
      method: "POST",
      body: JSON.stringify({ board_id: boardId, title }),
    }),
  update: (columnId, data) =>
    request(`/api/columns/${columnId}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  delete: (columnId) =>
    request(`/api/columns/${columnId}`, { method: "DELETE" }),
};

export const cardsAPI = {
  getByBoard: (boardId) => request(`/api/boards/${boardId}/cards`),
  getById: (cardId) => request(`/api/cards/${cardId}`),
  create: (columnId, title, description = "", priority = "medium", assignee_id = null, deadline = null) =>
    request("/api/cards", {
      method: "POST",
      body: JSON.stringify({ column_id: columnId, title, description, priority, assignee_id, deadline }),
    }),
  update: (cardId, data) =>
    request(`/api/cards/${cardId}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  delete: (cardId) =>
    request(`/api/cards/${cardId}`, { method: "DELETE" }),
  move: (cardId, newColumnId, newPosition, version) =>
    request(`/api/cards/${cardId}/move?new_column_id=${newColumnId}&new_position=${newPosition}&version=${version}`, {
      method: "PUT",
    }),
};

export const usersAPI = {
  getAll: () => request("/api/users/all"), // <-- Изменили путь
};

export const commentsAPI = {
  getByCard: (cardId) => request(`/api/cards/${cardId}/comments`),
  add: (cardId, content) =>
    request(`/api/cards/${cardId}/comments`, {
      method: "POST",
      body: JSON.stringify({ content }),
    }),
  delete: (commentId) =>
    request(`/api/comments/${commentId}`, { method: "DELETE" }),
};
