"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  Alert, Box, Button, Divider, Grid, Stack, TextField, Typography,
} from "@mui/material";
import AuthBrandPanel from "../../components/AuthBrandPanel";
import { useAuth } from "../../components/AuthProvider";
import { I18nProvider, LanguageSwitcher } from "../i18n";

function LoginForm() {
  const { login, providers, user } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (user) router.replace("/app");
  }, [user, router]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await login(email, password);
      router.replace("/app");
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
            p: { xs: 3, md: 6 }, maxWidth: 480, mx: "auto", height: "100%",
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
            Sign in to your underwriting workspace. New here?{" "}
            <Link href="/register" style={{ color: "#1f4dff", fontWeight: 600 }}>
              Create an account
            </Link>
          </Typography>

          {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}

          <Stack spacing={2} sx={{ mb: 3 }}>
            <Button
              fullWidth variant="outlined" disabled={!providers.x} onClick={() => social("x")}
              sx={{ textTransform: "none", color: "text.primary", borderColor: "divider" }}
            >
              {providers.x ? "Continue with X" : "Continue with X (not configured)"}
            </Button>
            <Button
              fullWidth variant="outlined" disabled={!providers.facebook} onClick={() => social("facebook")}
              sx={{ textTransform: "none", color: "text.primary", borderColor: "divider" }}
            >
              {providers.facebook ? "Continue with Facebook" : "Continue with Facebook (not configured)"}
            </Button>
          </Stack>

          <Divider sx={{ mb: 3 }}>or</Divider>

          <Box component="form" onSubmit={submit}>
            <Stack spacing={2.5}>
              <TextField
                label="Email" type="email" value={email} required fullWidth
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
        </Box>
      </Grid>
    </Grid>
  );
}

export default function LoginPage() {
  return (
    <I18nProvider>
      <LoginForm />
    </I18nProvider>
  );
}
