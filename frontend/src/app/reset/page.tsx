"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import {
  Alert, Box, Button, Stack, TextField, Typography,
} from "@mui/material";
import { I18nProvider, LanguageSwitcher, useT } from "../i18n";

function ResetForm() {
  const { t } = useT();
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
      setError(t("atLeast8"));
      return;
    }
    if (password !== confirm) {
      setError(t("passwordMismatch"));
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
          {t("resetMissingToken")}{" "}
          <Link href="/forgot" style={{ fontWeight: 600 }}>{t("requestNew")}</Link>
        </Alert>
      </Box>
    );
  }

  return (
    <Box sx={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", p: 3 }}>
      <Box sx={{ width: "100%", maxWidth: 420 }}>
        <Stack direction="row" justifyContent="flex-end" sx={{ mb: 2 }}>
          <LanguageSwitcher />
        </Stack>
        <Typography variant="caption" sx={{ letterSpacing: 1.4, fontWeight: 700, color: "text.secondary", display: "block", mb: 1 }}>
          {t("resetKicker")}
        </Typography>
        <Typography variant="h3" sx={{ mb: 1 }}>
          {t("resetTitle")}
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 4 }}>
          {t("resetSub")}
        </Typography>

        {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}

        <Box component="form" onSubmit={submit}>
          <Stack spacing={2.5}>
            <TextField
              label={t("newPassword")} type="password" value={password} required fullWidth autoFocus
              helperText={t("atLeast8")}
              onChange={(e) => setPassword(e.target.value)}
            />
            <TextField
              label={t("confirmPassword")} type="password" value={confirm} required fullWidth
              onChange={(e) => setConfirm(e.target.value)}
            />
            <Button type="submit" variant="contained" size="large" disabled={busy} fullWidth>
              {busy ? t("updating") : t("updatePassword")}
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
