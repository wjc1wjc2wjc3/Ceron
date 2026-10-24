"use client";

import Link from "next/link";
import { useState } from "react";
import {
  Alert, Box, Button, Link as MuiLink, Stack, TextField, Typography,
} from "@mui/material";
import LockResetIcon from "@mui/icons-material/LockReset";
import { I18nProvider } from "../i18n";

function ForgotForm() {
  const [email, setEmail] = useState("");
  const [done, setDone] = useState(false);
  const [devLink, setDevLink] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const r = await fetch("/py/v1/auth/password/forgot", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data?.detail || "request_failed");
      setDevLink(data.dev_link || "");
      setDone(true);
    } catch (err: any) {
      setError(err?.message || "request_failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Box sx={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", p: 3 }}>
      <Box sx={{ width: "100%", maxWidth: 420 }}>
        <LockResetIcon sx={{ color: "primary.main", fontSize: 34, mb: 2 }} />
        <Typography variant="caption" sx={{ letterSpacing: 1.4, fontWeight: 700, color: "text.secondary", display: "block", mb: 1 }}>
          ACCOUNT RECOVERY
        </Typography>
        <Typography variant="h3" sx={{ mb: 1 }}>
          Forgot password?
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 4 }}>
          Enter the email on your Ceron account and we will send a reset link (valid 30 minutes).
        </Typography>

        {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}
        {done && (
          <>
            <Alert severity="success" sx={{ mb: 3 }}>
              If an account exists for that email, a reset link is on its way.
            </Alert>
            {devLink && (
              <Alert severity="info" sx={{ mb: 3 }}>
                Development mode (no SMTP configured) —{" "}
                <MuiLink href={devLink} sx={{ fontWeight: 700 }}>open the reset link</MuiLink>
              </Alert>
            )}
          </>
        )}

        {!done && (
          <Box component="form" onSubmit={submit}>
            <Stack spacing={2.5}>
              <TextField
                label="Email" type="email" value={email} required fullWidth autoFocus
                onChange={(e) => setEmail(e.target.value)}
              />
              <Button type="submit" variant="contained" size="large" disabled={busy} fullWidth>
                {busy ? "Sending…" : "Send reset link"}
              </Button>
            </Stack>
          </Box>
        )}

        <Typography variant="body2" color="text.secondary" sx={{ mt: 4 }}>
          Back to{" "}
          <Link href="/login" style={{ color: "#1f4dff", fontWeight: 600 }}>
            sign in
          </Link>
        </Typography>
      </Box>
    </Box>
  );
}

export default function ForgotPasswordPage() {
  return (
    <I18nProvider>
      <ForgotForm />
    </I18nProvider>
  );
}
