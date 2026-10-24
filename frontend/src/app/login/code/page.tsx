"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import {
  Alert, Box, Button, Stack, TextField, Typography,
} from "@mui/material";
import MarkEmailReadIcon from "@mui/icons-material/MarkEmailRead";
import { I18nProvider, LanguageSwitcher, useT } from "../../i18n";
import { useAuth } from "../../../components/AuthProvider";

type Stage = "request" | "verify";

function EmailCodeForm() {
  const { t, tf } = useT();
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
      setNotice(t("codeSent"));
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
        <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
          <MarkEmailReadIcon sx={{ color: "primary.main", fontSize: 34 }} />
          <LanguageSwitcher />
        </Stack>
        <Typography variant="caption" sx={{ letterSpacing: 1.4, fontWeight: 700, color: "text.secondary", display: "block", mb: 1 }}>
          {t("codeKicker")}
        </Typography>
        <Typography variant="h3" sx={{ mb: 1 }}>
          {stage === "request" ? t("codeTitleRequest") : t("codeTitleVerify")}
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 4 }}>
          {stage === "request" ? t("codeSubRequest") : tf("codeSubVerify", { email })}
        </Typography>

        {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}
        {notice && <Alert severity="success" sx={{ mb: 3 }}>{notice}</Alert>}
        {devCode && (
          <Alert severity="info" sx={{ mb: 3 }}>
            {t("devCodeHint")} <strong>{devCode}</strong>
          </Alert>
        )}

        {stage === "request" ? (
          <Box component="form" onSubmit={requestCode}>
            <Stack spacing={2.5}>
              <TextField
                label={t("email")} type="email" value={email} required fullWidth autoFocus
                onChange={(e) => setEmail(e.target.value)}
              />
              <Button type="submit" variant="contained" size="large" disabled={busy} fullWidth>
                {busy ? t("sending") : t("emailMeCode")}
              </Button>
            </Stack>
          </Box>
        ) : (
          <Box component="form" onSubmit={verifyCode}>
            <Stack spacing={2.5}>
              <TextField
                label={t("code6")} value={code} required fullWidth autoFocus
                inputProps={{ maxLength: 6, pattern: "[0-9]*" }}
                onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
              />
              <Button type="submit" variant="contained" size="large" disabled={busy || code.length < 6} fullWidth>
                {busy ? t("verifying") : t("verifySignIn")}
              </Button>
              <Button variant="text" size="small" onClick={() => { setStage("request"); setError(""); }}>
                {t("useDifferentEmail")}
              </Button>
            </Stack>
          </Box>
        )}

        <Typography variant="body2" color="text.secondary" sx={{ mt: 4 }}>
          {t("rememberPassword")}{" "}
          <Link href="/login" style={{ color: "#1f4dff", fontWeight: 600 }}>
            {t("signInPassword")}
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
