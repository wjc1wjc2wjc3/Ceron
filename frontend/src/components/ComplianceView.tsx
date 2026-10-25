"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Alert, Box, Button, Card, CardContent, Chip, Divider, Grid, Paper, Snackbar, Stack, Tab,
  Table, TableBody, TableCell, TableHead, TableRow, Tabs, TextField, Typography,
} from "@mui/material";
import RefreshIcon from "@mui/icons-material/Refresh";
import GavelIcon from "@mui/icons-material/Gavel";
import { canOpsWrite, useAuth } from "./AuthProvider";
import { useT } from "../app/i18n";

function token(): string {
  if (typeof document === "undefined") return "";
  return localStorage.getItem("ceron_token") || "";
}

async function api(path: string, init?: RequestInit) {
  const res = await fetch(path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token()}`,
      ...(init?.headers || {}),
    },
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data?.detail || data?.error || `request_failed_${res.status}`);
  return data;
}

interface AlertRec {
  id: string | number;
  ts: string;
  name: string;
  reason: string;
  lists: string[];
  status: string;
}

interface SarRec {
  id: string;
  name: string;
  reason: string;
  vertical: string;
  status: string;
  ts: string;
}

const VERTICALS = [
  "insurance_hk", "trust", "family_office",
  "banking_mortgage", "securities_suitability", "mpf", "fund_ofc_lpf",
];

const STATUS_COLOR: Record<string, "default" | "primary" | "success" | "warning" | "error"> = {
  draft: "warning",
  submitted: "success",
  closed: "default",
  open: "error",
  acknowledged: "primary",
  resolved: "default",
};

export default function ComplianceView() {
  const { t } = useT();
  const { user } = useAuth();
  const canWrite = canOpsWrite(user);   // RBAC：写操作按角色显隐
  const [tab, setTab] = useState(0);
  const [alerts, setAlerts] = useState<AlertRec[]>([]);
  const [sars, setSars] = useState<SarRec[]>([]);
  const [mi, setMi] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState("");

  const [sarName, setSarName] = useState("");
  const [sarReason, setSarReason] = useState("");
  const [sarVertical, setSarVertical] = useState(VERTICALS[0]);

  const refresh = useCallback(async () => {
    const [a, s, m] = await Promise.all([
      api("/py/v1/monitoring/alerts").catch(() => ({ alerts: [] })),
      api("/py/v1/sar").catch(() => ({ sars: [] })),
      api("/py/v1/mi").catch(() => null),
    ]);
    setAlerts(a.alerts || []);
    setSars(s.sars || []);
    setMi(m);
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function scan() {
    setBusy(true);
    try {
      const r = await api("/py/v1/monitoring/scan", { method: "POST" });
      setToast(`${t("scanNow")}: ${r.scanned} / ${(r.hits || []).length}`);
      await refresh();
    } catch (e: any) {
      setToast(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function setAlertStatus(id: string | number, status: string) {
    try {
      await api(`/py/v1/monitoring/alerts/${id}`, {
        method: "PATCH", body: JSON.stringify({ status }),
      });
      await refresh();
    } catch (e: any) {
      setToast(e.message);
    }
  }

  async function alertToSar(a: AlertRec) {
    try {
      const s = await api(`/py/v1/monitoring/alerts/${a.id}/sar`, { method: "POST" });
      setToast(`${t("alertToSar")} → ${s.id}`);
      setTab(1);
      await refresh();
    } catch (e: any) {
      setToast(e.message);
    }
  }

  async function createSar() {
    if (!sarName.trim()) return;
    try {
      await api("/py/v1/sar", {
        method: "POST",
        body: JSON.stringify({
          name: sarName.trim(), reason: sarReason.trim(), vertical: sarVertical,
        }),
      });
      setSarName("");
      setSarReason("");
      await refresh();
    } catch (e: any) {
      setToast(e.message);
    }
  }

  async function setSarStatus(id: string, status: string) {
    try {
      await api(`/py/v1/sar/${id}/status`, { method: "POST", body: JSON.stringify({ status }) });
      await refresh();
    } catch (e: any) {
      setToast(e.message);
    }
  }

  const openAlerts = alerts.filter((a) => a.status === "open");

  return (
    <Stack spacing={2} sx={{ p: { xs: 2, md: 3 }, maxWidth: 1200, mx: "auto" }}>
      <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
        <Box>
          <Stack direction="row" spacing={1} alignItems="center">
            <Typography variant="h4" fontWeight={800}>{t("monTitle")}</Typography>
            <Chip size="small" variant="outlined"
              label={`${t("roleLabel")}: ${user?.role || "analyst"}`} />
          </Stack>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            {t("monSubtitle")}
          </Typography>
        </Box>
        <Chip
          color={openAlerts.length ? "error" : "success"} size="small"
          label={`${openAlerts.length} ${t("alerts")}`}
        />
      </Stack>

      <Tabs value={tab} onChange={(_, v) => setTab(v)}>
        <Tab label={t("tabAlerts")} />
        <Tab label={t("tabSar")} />
        <Tab label={t("tabMi")} />
      </Tabs>

      {/* ============ 监控收件箱 ============ */}
      {tab === 0 && (
        <Paper variant="outlined">
          <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ p: 2 }}>
            <Typography variant="h6">{t("monitoring")}</Typography>
            <Button
              size="small" variant="outlined" disabled={busy}
              startIcon={<RefreshIcon />} onClick={scan}
            >
              {t("scanNow")}
            </Button>
          </Stack>
          <Divider />
          {!alerts.length ? (
            <Alert severity="success" sx={{ m: 2 }}>{t("noAlerts")}</Alert>
          ) : (
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>{t("alertCreated")}</TableCell>
                  <TableCell>{t("sarName")}</TableCell>
                  <TableCell>{t("alertReasonLabel")}</TableCell>
                  <TableCell>{t("alertLists")}</TableCell>
                  <TableCell>{t("alertStatus")}</TableCell>
                  <TableCell align="right">{t("alertActions")}</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {alerts.map((a) => (
                  <TableRow key={a.id} hover>
                    <TableCell sx={{ whiteSpace: "nowrap" }}>{a.ts}</TableCell>
                    <TableCell>{a.name}</TableCell>
                    <TableCell>{a.reason}</TableCell>
                    <TableCell>
                      <Stack direction="row" spacing={0.5} flexWrap="wrap">
                        {(a.lists || []).map((l) => (
                          <Chip key={l} size="small" variant="outlined" label={l} />
                        ))}
                      </Stack>
                    </TableCell>
                    <TableCell>
                      <Chip
                        size="small" label={a.status}
                        color={STATUS_COLOR[a.status] || "default"}
                      />
                    </TableCell>
                    <TableCell align="right">
                      <Stack direction="row" spacing={1} justifyContent="flex-end">
                        {a.status === "open" && canWrite && (
                          <Button size="small" onClick={() => setAlertStatus(a.id, "acknowledged")}>
                            {t("alertAck")}
                          </Button>
                        )}
                        {a.status !== "resolved" && canWrite && (
                          <Button size="small" onClick={() => setAlertStatus(a.id, "resolved")}>
                            {t("alertResolve")}
                          </Button>
                        )}
                        {canWrite ? (
                          <Button
                            size="small" variant="contained"
                            startIcon={<GavelIcon />}
                            onClick={() => alertToSar(a)}
                          >
                            {t("alertToSar")}
                          </Button>
                        ) : (
                          <Typography variant="caption" color="text.secondary">
                            {t("readonlyRole")}
                          </Typography>
                        )}
                      </Stack>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </Paper>
      )}

      {/* ============ SAR 工作流 ============ */}
      {tab === 1 && (
        <Grid container spacing={2}>
          <Grid item xs={12} md={4}>
            <Paper variant="outlined" sx={{ p: 2 }}>
              <Typography variant="h6" sx={{ mb: 1.5 }}>{t("sarTitle")}</Typography>
              <Stack spacing={1.5}>
                <TextField
                  size="small" label={t("sarName")} value={sarName}
                  onChange={(e) => setSarName(e.target.value)} fullWidth
                />
                <TextField
                  select size="small" label={t("sarVertical")} value={sarVertical}
                  onChange={(e) => setSarVertical(e.target.value)}
                  SelectProps={{ native: true }} fullWidth
                >
                  {VERTICALS.map((v) => <option key={v} value={v}>{v}</option>)}
                </TextField>
                <TextField
                  size="small" label={t("sarReason")} value={sarReason} multiline minRows={3}
                  onChange={(e) => setSarReason(e.target.value)} fullWidth
                />
                <Button variant="contained" onClick={createSar} disabled={!sarName.trim()}>
                  {t("createSar")}
                </Button>
              </Stack>
            </Paper>
          </Grid>
          <Grid item xs={12} md={8}>
            <Paper variant="outlined">
              <Stack direction="row" justifyContent="space-between" sx={{ p: 2 }}>
                <Typography variant="h6">{t("sarWorkflow")}</Typography>
                <Typography variant="caption" color="text.secondary">
                  {t("sarFlowHint")}
                </Typography>
              </Stack>
              <Divider />
              {!sars.length ? (
                <Alert severity="info" sx={{ m: 2 }}>{t("sarEmpty")}</Alert>
              ) : (
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>{t("sarId")}</TableCell>
                      <TableCell>{t("sarName")}</TableCell>
                      <TableCell>{t("sarReason")}</TableCell>
                      <TableCell>{t("sarStatus")}</TableCell>
                      <TableCell align="right">{t("alertActions")}</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {sars.map((s) => (
                      <TableRow key={s.id} hover>
                        <TableCell sx={{ whiteSpace: "nowrap" }}>{s.id}</TableCell>
                        <TableCell>{s.name}</TableCell>
                        <TableCell>{s.reason}</TableCell>
                        <TableCell>
                          <Chip size="small" label={s.status} color={STATUS_COLOR[s.status] || "default"} />
                        </TableCell>
                        <TableCell align="right">
                          <Stack direction="row" spacing={1} justifyContent="flex-end">
                            {s.status === "draft" && canWrite && (
                              <Button size="small" variant="contained"
                                onClick={() => setSarStatus(s.id, "submitted")}>
                                {t("sarSubmit")}
                              </Button>
                            )}
                            {s.status === "submitted" && canWrite && (
                              <Button size="small" onClick={() => setSarStatus(s.id, "closed")}>
                                {t("sarClose")}
                              </Button>
                            )}
                            {s.status === "closed" && canWrite && (
                              <Button size="small" onClick={() => setSarStatus(s.id, "draft")}>
                                {t("sarReopen")}
                              </Button>
                            )}
                            {!canWrite && (
                              <Typography variant="caption" color="text.secondary">
                                {t("readonlyRole")}
                              </Typography>
                            )}
                          </Stack>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </Paper>
          </Grid>
        </Grid>
      )}

      {/* ============ 监管 MI 看板 ============ */}
      {tab === 2 && (
        <Paper variant="outlined" sx={{ p: 2 }}>
          <Typography variant="h6" sx={{ mb: 2 }}>{t("miTitle")}</Typography>
          {!mi ? (
            <Typography variant="body2" color="text.secondary">…</Typography>
          ) : (
            <>
              <Grid container spacing={2}>
                {[
                  { label: t("miTotal"), value: mi.total_decisions },
                  { label: t("miHigh"), value: mi.high_risk_count },
                  { label: t("miAlerts"), value: mi.open_alerts },
                  { label: t("miSarTotal"), value: mi.sars_total },
                ].map((k) => (
                  <Grid item xs={6} md={3} key={k.label}>
                    <Card variant="outlined">
                      <CardContent>
                        <Typography variant="caption" color="text.secondary">{k.label}</Typography>
                        <Typography variant="h4" fontWeight={800}>{String(k.value)}</Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                ))}
              </Grid>
              <Divider sx={{ my: 3 }} />
              <Grid container spacing={3}>
                <Grid item xs={12} md={6}>
                  <Typography variant="subtitle2" sx={{ mb: 1 }}>{t("miByVertical")}</Typography>
                  <Stack spacing={0.5}>
                    {Object.entries(mi.by_vertical || {}).map(([k, v]) => (
                      <Stack key={k} direction="row" justifyContent="space-between">
                        <Typography variant="body2">{k}</Typography>
                        <Chip size="small" variant="outlined" label={String(v)} />
                      </Stack>
                    ))}
                    {!Object.keys(mi.by_vertical || {}).length && (
                      <Typography variant="caption" color="text.secondary">—</Typography>
                    )}
                  </Stack>
                </Grid>
                <Grid item xs={12} md={6}>
                  <Typography variant="subtitle2" sx={{ mb: 1 }}>{t("miByAction")}</Typography>
                  <Stack spacing={0.5}>
                    {Object.entries(mi.by_action || {}).map(([k, v]) => (
                      <Stack key={k} direction="row" justifyContent="space-between">
                        <Typography variant="body2">{k}</Typography>
                        <Chip size="small" variant="outlined" label={String(v)} />
                      </Stack>
                    ))}
                    {!Object.keys(mi.by_action || {}).length && (
                      <Typography variant="caption" color="text.secondary">—</Typography>
                    )}
                  </Stack>
                </Grid>
              </Grid>
              <Typography variant="caption" color="text.secondary" sx={{ mt: 3, display: "block" }}>
                {t("generatedAt")}：{mi.generated_at}
              </Typography>
            </>
          )}
        </Paper>
      )}

      <Snackbar
        open={Boolean(toast)} autoHideDuration={4000} onClose={() => setToast("")}
        message={toast}
      />
    </Stack>
  );
}
