"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Alert, Chip, Divider, Paper, Snackbar, Stack, Switch, Table, TableBody, TableCell,
  TableHead, TableRow, TextField, Typography,
} from "@mui/material";
import NavBar from "../../../components/NavBar";
import { I18nProvider, useT } from "../../i18n";

interface RuleState {
  enabled: boolean;
  snoozed_until: string | null;
}

interface Rule {
  id: string;
  gate: string;
  vertical: string;
  severity: string;
  delta: number;
  fields: string[];
  reason: Record<string, string>;
  state: RuleState;
}

const SEVERITY_COLOR: Record<string, "default" | "info" | "warning" | "error"> = {
  low: "default",
  medium: "info",
  high: "warning",
  critical: "error",
};

async function api(path: string, init?: RequestInit) {
  const res = await fetch(path, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data?.detail || data?.error || `request_failed_${res.status}`);
  return data;
}

/** 把 datetime-local 的值转成 ISO；空串表示清除休眠。 */
function toIso(value: string): string | null {
  if (!value) return null;
  const d = new Date(value);
  return isNaN(d.getTime()) ? null : d.toISOString();
}

function RulesView() {
  const { t } = useT();
  const [pack, setPack] = useState<{ version: string; count: number; rules: Rule[] } | null>(null);
  const [locale] = useState<string>(
    typeof document !== "undefined" && document.cookie.includes("lang=zh-CN") ? "zh-CN" : "zh-HK"
  );
  const [error, setError] = useState("");
  const [toast, setToast] = useState("");
  const [busyId, setBusyId] = useState("");

  const load = useCallback(async () => {
    try {
      setPack(await api("/py/v1/rules"));
      setError("");
    } catch (e: any) {
      setError(e.message);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function setState(id: string, body: { enabled?: boolean; snoozed_until?: string | null }) {
    setBusyId(id);
    try {
      await api(`/py/v1/rules/${encodeURIComponent(id)}/state`, {
        method: "POST", body: JSON.stringify(body),
      });
      setToast(t("rulesSaved"));
      await load();
    } catch (e: any) {
      setToast(e.message);
    } finally {
      setBusyId("");
    }
  }

  const activeCount = pack?.rules.filter(
    (r) => r.state?.enabled !== false && !r.state?.snoozed_until
  ).length ?? 0;

  return (
    <>
      <NavBar />
      <Stack spacing={2} sx={{ p: { xs: 2, md: 3 }, maxWidth: 1200, mx: "auto" }}>
        <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
          <div>
            <Typography variant="h4" fontWeight={800}>{t("rulesTitle")}</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
              {t("rulesSubtitle")}
            </Typography>
          </div>
          <Stack direction="row" spacing={1}>
            <Chip size="small" label={`${t("rulesVersion")}: ${pack?.version ?? "…"}`} />
            <Chip size="small" color="primary" label={`${activeCount}/${pack?.count ?? 0} ${t("rulesActive")}`} />
          </Stack>
        </Stack>

        {error && <Alert severity="error">{error}</Alert>}

        <Paper variant="outlined">
          {!pack ? (
            <Typography sx={{ p: 2 }} variant="body2" color="text.secondary">…</Typography>
          ) : (
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>{t("rulesId")}</TableCell>
                  <TableCell>{t("rulesGate")}</TableCell>
                  <TableCell>{t("rulesVertical")}</TableCell>
                  <TableCell>{t("rulesSeverity")}</TableCell>
                  <TableCell align="right">{t("rulesDelta")}</TableCell>
                  <TableCell>{t("rulesEnabled")}</TableCell>
                  <TableCell>{t("rulesSnoozeUntil")}</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {pack.rules.map((r) => {
                  const disabled = r.state?.enabled === false;
                  return (
                    <TableRow key={r.id} hover>
                      <TableCell sx={{ fontFamily: "monospace", fontSize: 12 }}>{r.id}</TableCell>
                      <TableCell>{r.gate}</TableCell>
                      <TableCell>{r.vertical}</TableCell>
                      <TableCell>
                        <Chip
                          size="small" label={r.severity}
                          color={SEVERITY_COLOR[r.severity] || "default"}
                        />
                      </TableCell>
                      <TableCell align="right">{r.delta}</TableCell>
                      <TableCell>
                        <Stack direction="row" alignItems="center" spacing={1}>
                          <Switch
                            size="small"
                            checked={!disabled}
                            disabled={busyId === r.id}
                            onChange={(e) => setState(r.id, { enabled: e.target.checked })}
                          />
                          {disabled && (
                            <Chip size="small" color="error" label={t("rulesDisabled")} />
                          )}
                        </Stack>
                      </TableCell>
                      <TableCell>
                        <Stack direction="row" spacing={1} alignItems="center">
                          <TextField
                            size="small" type="datetime-local"
                            value={(r.state?.snoozed_until || "").slice(0, 16)}
                            disabled={busyId === r.id}
                            onChange={(e) => {
                              const iso = toIso(e.target.value);
                              if (iso) setState(r.id, { snoozed_until: iso });
                            }}
                            InputLabelProps={{ shrink: true }}
                          />
                          {r.state?.snoozed_until && (
                            <Chip
                              size="small" color="warning" variant="outlined"
                              label={t("rulesSnoozed")}
                              onDelete={() => setState(r.id, { snoozed_until: "" })}
                            />
                          )}
                        </Stack>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </Paper>

        <Divider sx={{ my: 2 }} />

        <Typography variant="subtitle2">{t("rulesReasonPreview")}</Typography>
        <Stack spacing={0.5}>
          {(pack?.rules || []).slice(0, 6).map((r) => (
            <Typography key={r.id} variant="caption" color="text.secondary">
              <code>{r.id}</code> — {r.reason?.[locale] || r.reason?.["zh-HK"] || ""}
            </Typography>
          ))}
        </Stack>
      </Stack>

      <Snackbar
        open={Boolean(toast)} autoHideDuration={3000} onClose={() => setToast("")}
        message={toast}
      />
    </>
  );
}

export default function RulesPage() {
  return (
    <I18nProvider>
      <RulesView />
    </I18nProvider>
  );
}
