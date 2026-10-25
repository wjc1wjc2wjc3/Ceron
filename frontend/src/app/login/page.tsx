"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import {
  Alert, Box, Button, Checkbox, Divider, FormControlLabel, Grid, Link as MuiLink, Stack, TextField, Typography,
} from "@mui/material";
import AuthBrandPanel from "../../components/AuthBrandPanel";
import { useAuth } from "../../components/AuthProvider";
import { I18nProvider, LanguageSwitcher, useT } from "../i18n";

const REMEMBER_KEY = "ceron_credentials";

/** 记住账号和密码：写入本地 JSON；读取用于预填。仅前端便利，凭据以明文存于 localStorage。 */
function saveCredentials(email: string, password: string) {
  try {
    localStorage.setItem(REMEMBER_KEY, JSON.stringify({ email, password }));
  } catch { /* 隐私模式等场景忽略 */ }
}
function clearCredentials() {
  try { localStorage.removeItem(REMEMBER_KEY); } catch { /* ignore */ }
}
function readCredentials(): { email: string; password: string } | null {
  try {
    const raw = localStorage.getItem(REMEMBER_KEY);
    if (!raw) return null;
    const v = JSON.parse(raw);
    if (v && typeof v.email === "string" && typeof v.password === "string") return v;
  } catch { /* ignore */ }
  return null;
}

function LoginForm() {
  const { t, tf } = useT();
  const { login, providers, user } = useAuth();
  const router = useRouter();
  const params = useSearchParams();
  const next = params.get("next") || "/app";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(true); // 默认选中：记住账号和密码
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  // 启动时若存在已保存凭据，预填并默认勾选“记住”
  useEffect(() => {
    const saved = readCredentials();
    if (saved) {
      setEmail(saved.email);
      setPassword(saved.password);
      setRemember(true);
    }
  }, []);

  useEffect(() => {
    if (user) router.replace(next);
  }, [user, router, next]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await login(email, password);
      if (remember) saveCredentials(email, password);
      else clearCredentials();
      router.replace(next);
    } catch (err: any) {
      setError(err?.message || "login_failed");
    } finally {
      setBusy(false);
    }
  }

  async function social(kind: "x" | "facebook") {
    setError("");
    try {
      const r = await fetch(`/py/v1/auth/${kind}/authorize`);
      const data = await r.json();
      if (!r.ok) throw new Error(data?.detail || "not_configured");
      window.location.href = data.authorization_url;
    } catch (err: any) {
      setError(err?.message || "social_login_unavailable");
    }
  }

  return (
    <Grid container sx={{ minHeight: "100vh" }}>
      <Grid item xs={12} md={5}>
        <AuthBrandPanel quoteKey="authQuoteLogin" personKey="authPersonLogin" />
      </Grid>

      <Grid item xs={12} md={7}>
        <Box
          sx={{
            p: { xs: 3, md: 6 }, maxWidth: 460, mx: "auto", height: "100%",
            display: "flex", flexDirection: "column", justifyContent: "center",
          }}
        >
          <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 4 }}>
            <Typography variant="caption" sx={{ letterSpacing: 1.4, fontWeight: 700, color: "text.secondary" }}>
              {t("loginKicker")}
            </Typography>
            <LanguageSwitcher />
          </Stack>

          <Typography variant="h3" sx={{ mb: 1 }}>
            {t("loginTitle")}
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 4 }}>
            {t("loginNewHere")}{" "}
            <MuiLink component={Link} href="/register" sx={{ color: "#1f4dff", fontWeight: 600 }}>
              {t("loginCreateAccount")}
            </MuiLink>
          </Typography>

          {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}

          {/* 邮箱密码登录：主路径，放在最上方 */}
          <Box component="form" onSubmit={submit}>
            <Stack spacing={2.5}>
              <TextField
                label={t("email")} type="email" value={email} required fullWidth autoFocus
                onChange={(e) => setEmail(e.target.value)}
              />
              <TextField
                label={t("password")} type="password" value={password} required fullWidth
                onChange={(e) => setPassword(e.target.value)}
              />
              <FormControlLabel
                control={
                  <Checkbox
                    checked={remember}
                    onChange={(e) => setRemember(e.target.checked)}
                    size="small"
                    sx={{ color: "#1f4dff", "&.Mui-checked": { color: "#1f4dff" } }}
                  />
                }
                label={t("rememberMe")}
                sx={{ alignSelf: "flex-start", mt: -1 }}
              />
              <Button type="submit" variant="contained" size="large" disabled={busy} fullWidth>
                {busy ? t("signingIn") : t("signIn")}
              </Button>
            </Stack>
          </Box>

          <Stack direction="row" justifyContent="space-between" sx={{ mt: 2 }}>
            <MuiLink
              component={Link} href="/login/code"
              sx={{ fontSize: 13, color: "text.secondary", cursor: "pointer" }}
            >
              {t("loginCodeInstead")}
            </MuiLink>
            <MuiLink component={Link} href="/forgot" sx={{ fontSize: 13, color: "#1f4dff", fontWeight: 600 }}>
              {t("forgotPassword")}
            </MuiLink>
          </Stack>

          {/* 第三方登录降为次要选项 */}
          <Divider sx={{ my: 4 }}>
            <Typography variant="caption" color="text.secondary">{t("orContinue")}</Typography>
          </Divider>
          <Stack direction="row" spacing={1.5}>
            <Button
              fullWidth variant="text" size="small" disabled={!providers.x} onClick={() => social("x")}
              sx={{ color: "text.secondary", border: 1, borderColor: "divider", borderRadius: 999 }}
            >
              {providers.x ? "X" : tf("socialUnset", { provider: "X" })}
            </Button>
            <Button
              fullWidth variant="text" size="small" disabled={!providers.facebook} onClick={() => social("facebook")}
              sx={{ color: "text.secondary", border: 1, borderColor: "divider", borderRadius: 999 }}
            >
              {providers.facebook ? "Facebook" : tf("socialUnset", { provider: "Facebook" })}
            </Button>
          </Stack>
          <Typography variant="caption" color="text.secondary" sx={{ mt: 2, display: "block", textAlign: "center" }}>
            {t("socialHint")}
          </Typography>
        </Box>
      </Grid>
    </Grid>
  );
}

function LoginInner() {
  return (
    <Suspense fallback={<Box sx={{ minHeight: "100vh" }} />}>
      <LoginForm />
    </Suspense>
  );
}

export default function LoginPage() {
  return (
    <I18nProvider>
      <LoginInner />
    </I18nProvider>
  );
}
