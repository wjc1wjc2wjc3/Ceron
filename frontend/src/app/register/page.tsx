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
              <TextField label="Full name" value={name} fullWidth onChange={(e) => setName(e.target.value)} />
              <TextField
                label="Work email" type="email" value={email} required fullWidth
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

          <Typography variant="caption" color="text.secondary" sx={{ mt: 3, display: "block" }}>
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
