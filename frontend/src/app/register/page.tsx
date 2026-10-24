"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  Alert, Box, Button, Divider, Grid, Link as MuiLink, Stack, TextField, Typography,
} from "@mui/material";
import AuthBrandPanel from "../../components/AuthBrandPanel";
import { useAuth } from "../../components/AuthProvider";
import { I18nProvider, LanguageSwitcher } from "../i18n";

function RegisterForm() {
  const { register, providers, user } = useAuth();
  const router = useRouter();
  const [name, setName] = useState("");
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
      await register(email, password, name);
      router.replace("/app");
    } catch (err: any) {
      setError(err?.message || "register_failed");
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
          quoteKey="Compliance gates used to live in a spreadsheet. Now they run inside the pipeline."
          personKey="Head of Compliance · Family office, Central"
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
              GET STARTED
            </Typography>
            <LanguageSwitcher />
          </Stack>

          <Typography variant="h3" sx={{ mb: 1 }}>
            Create your account
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 4 }}>
            Start with the free sandbox — mock data sources included. Already have an account?{" "}
            <Link href="/login" style={{ color: "#1f4dff", fontWeight: 600 }}>
              Sign in
            </Link>
          </Typography>

          {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}

          {/* 邮箱注册：主路径，放在最上方 */}
          <Box component="form" onSubmit={submit}>
            <Stack spacing={2.5}>
              <TextField label="Full name" value={name} fullWidth onChange={(e) => setName(e.target.value)} />
              <TextField
                label="Work email" type="email" value={email} required fullWidth autoFocus
                onChange={(e) => setEmail(e.target.value)}
              />
              <TextField
                label="Password" type="password" value={password} required fullWidth
                helperText="At least 8 characters"
                onChange={(e) => setPassword(e.target.value)}
              />
              <Button type="submit" variant="contained" size="large" disabled={busy} fullWidth>
                {busy ? "Creating account…" : "Create account"}
              </Button>
            </Stack>
          </Box>

          <Typography variant="body2" color="text.secondary" sx={{ mt: 2, fontSize: 13 }}>
            Prefer no password?{" "}
            <MuiLink component={Link} href="/login/code" sx={{ color: "#1f4dff", fontWeight: 600, fontSize: 13 }}>
              Sign in with an email code
            </MuiLink>
          </Typography>

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

          <Typography variant="caption" color="text.secondary" sx={{ mt: 4, display: "block" }}>
            By continuing you agree to our Terms and Privacy Policy.
          </Typography>
        </Box>
      </Grid>
    </Grid>
  );
}

export default function RegisterPage() {
  return (
    <I18nProvider>
      <RegisterForm />
    </I18nProvider>
  );
}
