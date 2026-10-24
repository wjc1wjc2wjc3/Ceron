"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

export interface AuthUser {
  id: string;
  email: string;
  name: string;
  provider: string;
}

export interface Providers {
  email: boolean;
  x: boolean;
  facebook: boolean;
}

interface AuthContextValue {
  user: AuthUser | null;
  loading: boolean;
  providers: Providers;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name?: string) => Promise<void>;
  logout: () => void;
  setToken: (token: string) => Promise<void>;
}

const TOKEN_KEY = "ceron_token";

const AuthContext = createContext<AuthContextValue | null>(null);

/** 令牌同时写入 cookie（便于 Next 中间件做服务端路由守卫）与 localStorage。 */
function persistToken(token: string | null) {
  if (typeof document === "undefined") return;
  if (token) {
    document.cookie = `${TOKEN_KEY}=${token}; path=/; max-age=604800; SameSite=Lax`;
    localStorage.setItem(TOKEN_KEY, token);
  } else {
    document.cookie = `${TOKEN_KEY}=; path=/; max-age=0; SameSite=Lax`;
    localStorage.removeItem(TOKEN_KEY);
  }
}

export function readToken(): string | null {
  if (typeof document === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, init);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data?.detail || data?.error || `request_failed_${res.status}`);
  }
  return data as T;
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [providers, setProviders] = useState<Providers>({ email: true, x: false, facebook: false });

  // 启动：恢复会话 + 拉取可用的登录方式
  useEffect(() => {
    (async () => {
      const token = readToken();
      if (token) {
        try {
          const data = await api<{ user: AuthUser }>("/py/v1/auth/me", {
            headers: { Authorization: `Bearer ${token}` },
          });
          setUser(data.user);
        } catch {
          persistToken(null); // 令牌失效，清理本地会话
        }
      }
      setLoading(false);
      try {
        const p = await api<{ providers: Providers }>("/py/v1/auth/providers");
        setProviders(p.providers);
      } catch {
        setProviders({ email: true, x: false, facebook: false });
      }
    })();
  }, []);

  const setToken = useCallback(async (token: string) => {
    persistToken(token);
    const data = await api<{ user: AuthUser }>("/py/v1/auth/me", {
      headers: { Authorization: `Bearer ${token}` },
    });
    setUser(data.user);
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const data = await api<{ token: string; user: AuthUser }>("/py/v1/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    persistToken(data.token);
    setUser(data.user);
  }, []);

  const register = useCallback(
    async (email: string, password: string, name = "") => {
      const data = await api<{ token: string; user: AuthUser }>("/py/v1/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password, name }),
      });
      persistToken(data.token);
      setUser(data.user);
    },
    []
  );

  const logout = useCallback(() => {
    persistToken(null);
    setUser(null);
    window.location.href = "/";
  }, []);

  const value = useMemo(
    () => ({ user, loading, providers, login, register, logout, setToken }),
    [user, loading, providers, login, register, logout, setToken]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
