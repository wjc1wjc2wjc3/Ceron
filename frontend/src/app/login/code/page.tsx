"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import {
  Alert, Box, Button, Stack, TextField, Typography,
} from "@mui/material";
import MarkEmailReadIcon from "@mui/icons-material/MarkEmailRead";
import { I18nProvider } from "../../i18n";
import { useAuth } from "../../../components/AuthProvider";

type Stage = "request" | "verify";

function EmailCodeForm() {
  const { setToken } = useAuth();
  const router = useRouter();
  const [stage, setStage] = useState<Stage>("request");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [devCode, setDevCode] = useState("");
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function requestCode(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const r = await fetch("/py/v1/auth/email/code", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, purpose: "login" }),
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data?.detail || "send_failed");
      setDevCode(data.dev_code || ""); // 仅 SMTP 未配置时返回，便于本地调试
      setNotice("We sent a 6-digit code to your inbox.");
      setStage("verify");
    } catch (err: any) {
      setError(err?.message || "send_failed");
    } finally {
      setBusy(false);
    }
  }

  async function verifyCode(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const r = await fetch("/py/v1/auth/email/verify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, code }),
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data?.detail || "verify_failed");
      await setToken(data.token);
      router.replace("/app");
    } catch (err: any) {
      setError(err?.message || "verify_failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Box sx={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", p: 3 }}>
      <Box sx={{ width: "100%", maxWidth: 420 }}>
        <MarkEmailReadIcon sx={{ color: "primary.main", fontSize: 34, mb: 2 }} />
        <Typography variant="caption" sx={{ letterSpacing: 1.4, fontWeight: 700, color: "text.secondary", display: "block", mb: 1 }}>
          PASSWORDLESS SIGN-IN
        </Typography>
        <Typography variant="h3" sx={{ mb: 1 }}>
          {stage === "request" ? "Sign in with email code" : "Enter your code"}
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 4 }}>
          {stage === "request"
            ? "No password needed — we email you a one-time code. New email? We create the account for you."
            : `We sent a 6-digit code to ${email}. It expires in 10 minutes.`}
        </Typography>

        {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}
        {notice && <Alert severity="success" sx={{ mb: 3 }}>{notice}</Alert>}
        {devCode && (
          <Alert severity="info" sx={{ mb: 3 }}>
            Development mode (no SMTP configured) — your code is <strong>{devCode}</strong>
          </Alert>
        )}

        {stage === "request" ? (
          <Box component="form" onSubmit={requestCode}>
            <Stack spacing={2.5}>
              <TextField
                label="Email" type="email" value={email} required fullWidth autoFocus
                onChange={(e) => setEmail(e.target.value)}
              />
              <Button type="submit" variant="contained" size="large" disabled={busy} fullWidth>
                {busy ? "Sending…" : "Email me a code"}
              </Button>
            </Stack>
          </Box>
        ) : (
          <Box component="form" onSubmit={verifyCode}>
            <Stack spacing={2.5}>
              <TextField
                label="6-digit code" value={code} required fullWidth autoFocus
                inputProps={{ maxLength: 6, pattern: "[0-9]*" }}
                onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
              />
              <Button type="submit" variant="contained" size="large" disabled={busy || code.length < 6} fullWidth>
                {busy ? "Verifying…" : "Verify and sign in"}
              </Button>
              <Button variant="text" size="small" onClick={() => { setStage("request"); setError(""); }}>
                Use a different email
              </Button>
            </Stack>
          </Box>
        )}

        <Typography variant="body2" color="text.secondary" sx={{ mt: 4 }}>
          Remember your password?{" "}
          <Link href="/login" style={{ color: "#1f4dff", fontWeight: 600 }}>
            Sign in with password
          </Link>
        </Typography>
      </Box>
    </Box>
  );
}

export default function EmailCodePage() {
  return (
    <I18nProvider>
      <EmailCodeForm />
    </I18nProvider>
  );
}
