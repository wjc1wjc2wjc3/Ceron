"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import {
  Alert, Box, Button, Divider, Grid, Link as MuiLink, Stack, TextField, Typography,
} from "@mui/material";
import AuthBrandPanel from "../../components/AuthBrandPanel";
import { useAuth } from "../../components/AuthProvider";
import { I18nProvider, LanguageSwitcher } from "../i18n";

function LoginForm() {
  const { login, providers, user } = useAuth();
  const router = useRouter();
  const params = useSearchParams();
  const next = params.get("next") || "/app";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (user) router.replace(next);
  }, [user, router, next]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await login(email, password);
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
        <AuthBrandPanel
          quoteKey="We stopped re-keying applications. Ceron returns a decision-ready file to our CRM in minutes."
          personKey="Operations Lead · Hong Kong insurance brokerage"
        />
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
              CERON CONSOLE
            </Typography>
            <LanguageSwitcher />
          </Stack>

          <Typography variant="h3" sx={{ mb: 1 }}>
            Welcome back
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 4 }}>
            New here?{" "}
            <MuiLink component={Link} href="/register" sx={{ color: "#1f4dff", fontWeight: 600 }}>
              Create an account
            </MuiLink>
          </Typography>

          {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}

          {/* 邮箱密码登录：主路径，放在最上方 */}
          <Box component="form" onSubmit={submit}>
            <Stack spacing={2.5}>
              <TextField
                label="Email" type="email" value={email} required fullWidth autoFocus
                onChange={(e) => setEmail(e.target.value)}
              />
              <TextField
                label="Password" type="password" value={password} required fullWidth
                onChange={(e) => setPassword(e.target.value)}
              />
              <Button type="submit" variant="contained" size="large" disabled={busy} fullWidth>
                {busy ? "Signing in…" : "Sign in"}
              </Button>
            </Stack>
          </Box>

          <Stack direction="row" justifyContent="space-between" sx={{ mt: 2 }}>
            <MuiLink
              component={Link} href="/login/code"
              sx={{ fontSize: 13, color: "text.secondary", cursor: "pointer" }}
            >
              Email me a code instead
            </MuiLink>
            <MuiLink component={Link} href="/forgot" sx={{ fontSize: 13, color: "#1f4dff", fontWeight: 600 }}>
              Forgot password?
            </MuiLink>
          </Stack>

          {/* 第三方登录降为次要选项 */}
          <Divider sx={{ my: 4 }}>
            <Typography variant="caption" color="text.secondary">or continue with</Typography>
          </Divider>
          <Stack direction="row" spacing={1.5}>
            <Button
              fullWidth variant="text" size="small" disabled={!providers.x} onClick={() => social("x")}
              sx={{ color: "text.secondary", border: 1, borderColor: "divider", borderRadius: 999 }}
            >
              {providers.x ? "X" : "X (unset)"}
            </Button>
            <Button
              fullWidth variant="text" size="small" disabled={!providers.facebook} onClick={() => social("facebook")}
              sx={{ color: "text.secondary", border: 1, borderColor: "divider", borderRadius: 999 }}
            >
              {providers.facebook ? "Facebook" : "Facebook (unset)"}
            </Button>
          </Stack>
          <Typography variant="caption" color="text.secondary" sx={{ mt: 2, display: "block", textAlign: "center" }}>
            Social login appears once X / Facebook credentials are configured.
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
