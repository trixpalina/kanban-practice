import { createContext, useState, useEffect, useContext } from "react";
import { authAPI } from "./api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const loadProfile = async (token) => {
    const profile = await authAPI.me();
    setUser({ token, ...profile });
  };

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (token) {
      loadProfile(token).catch(() => {
        localStorage.removeItem("token");
        setUser(null);
      }).finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

 const login = async (username, password) => {
  const data = await authAPI.login(username, password);
  localStorage.setItem("token", data.access_token);
  localStorage.setItem("username", username); // Сохраняем username
  setUser({ token: data.access_token, username });
};

  const register = async (username, email, password) => {
    await authAPI.register(username, email, password);
    return login(username, password);
  };

  const logout = () => {
    localStorage.removeItem("token");
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, login, register, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
