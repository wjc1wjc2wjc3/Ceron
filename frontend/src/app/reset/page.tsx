"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import {
  Alert, Box, Button, Stack, TextField, Typography,
} from "@mui/material";
import { I18nProvider } from "../i18n";

function ResetForm() {
  const params = useSearchParams();
  const router = useRouter();
  const token = params.get("token") || "";
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    if (password !== confirm) {
      setError("Passwords do not match.");
      return;
    }
    setBusy(true);
    try {
      const r = await fetch("/py/v1/auth/password/reset", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, new_password: password }),
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data?.detail || "reset_failed");
      router.replace("/login");
    } catch (err: any) {
      setError(err?.message || "reset_failed");
    } finally {
      setBusy(false);
    }
  }

  if (!token) {
    return (
      <Box sx={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", p: 3 }}>
        <Alert severity="error">
          This reset link is missing its token.{" "}
          <Link href="/forgot" style={{ fontWeight: 600 }}>Request a new one</Link>
        </Alert>
      </Box>
    );
  }

  return (
    <Box sx={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", p: 3 }}>
      <Box sx={{ width: "100%", maxWidth: 420 }}>
        <Typography variant="caption" sx={{ letterSpacing: 1.4, fontWeight: 700, color: "text.secondary", display: "block", mb: 1 }}>
          ACCOUNT RECOVERY
        </Typography>
        <Typography variant="h3" sx={{ mb: 1 }}>
          Set a new password
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 4 }}>
          Choose a password of at least 8 characters. The reset link is single-use.
        </Typography>

        {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}

        <Box component="form" onSubmit={submit}>
          <Stack spacing={2.5}>
            <TextField
              label="New password" type="password" value={password} required fullWidth autoFocus
              helperText="At least 8 characters"
              onChange={(e) => setPassword(e.target.value)}
            />
            <TextField
              label="Confirm password" type="password" value={confirm} required fullWidth
              onChange={(e) => setConfirm(e.target.value)}
            />
            <Button type="submit" variant="contained" size="large" disabled={busy} fullWidth>
              {busy ? "Updating…" : "Update password"}
            </Button>
          </Stack>
        </Box>
      </Box>
    </Box>
  );
}

function ResetInner() {
  return (
    <Suspense fallback={<Box sx={{ minHeight: "100vh" }} />}>
      <ResetForm />
    </Suspense>
  );
}

export default function ResetPasswordPage() {
  return (
    <I18nProvider>
      <ResetInner />
    </I18nProvider>
  );
}
