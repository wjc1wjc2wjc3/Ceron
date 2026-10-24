"use client";

import { useEffect, useState } from "react";
import {
  Button, Card, CardContent, Chip, Grid, Paper, Stack, TextField, Typography,
} from "@mui/material";
import { useT } from "../app/i18n";

export default function ComplianceView() {
  const { t } = useT();
  const [alerts, setAlerts] = useState<any[]>([]);
  const [sars, setSars] = useState<any[]>([]);
  const [mi, setMi] = useState<any>(null);
  const [sarName, setSarName] = useState("");
  const [sarReason, setSarReason] = useState("");

  async function refresh() {
    const a = await fetch("/py/v1/monitoring/alerts").then((r) => r.json());
    setAlerts(a.alerts || []);
    const s = await fetch("/py/v1/sar").then((r) => r.json());
    setSars(s.sars || []);
    const m = await fetch("/py/v1/mi").then((r) => r.json());
    setMi(m);
  }
  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function scan() {
    await fetch("/py/v1/monitoring/scan", { method: "POST" });
    refresh();
  }
  async function createSar() {
    if (!sarName) return;
    await fetch("/py/v1/sar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: sarName, reason: sarReason }),
    });
    setSarName("");
    setSarReason("");
    refresh();
  }

  return (
    <Grid container spacing={2} sx={{ mt: 0 }}>
      {/* 持续监控 */}
      <Grid item xs={12} md={4}>
        <Paper sx={{ p: 2 }}>
          <Stack direction="row" justifyContent="space-between" alignItems="center">
            <Typography variant="h6">{t("monitoring")}</Typography>
            <Button size="small" variant="outlined" onClick={scan}>
              {t("scanNow")}
            </Button>
          </Stack>
          <Typography variant="subtitle2" sx={{ mt: 1 }}>
            {t("alerts")}
          </Typography>
          {alerts.length === 0 ? (
            <Typography variant="body2" color="text.secondary">
              {t("noAlerts")}
            </Typography>
          ) : (
            alerts.map((a) => (
              <Card variant="outlined" sx={{ mt: 1, borderColor: "error.main" }} key={a.id}>
                <CardContent>
                  <Typography variant="body2">{a.name}</Typography>
                  <Typography variant="caption" color="text.secondary">
                    {a.reason} · {a.ts}
                  </Typography>
                </CardContent>
              </Card>
            ))
          )}
        </Paper>
      </Grid>

      {/* SAR 申报 */}
      <Grid item xs={12} md={4}>
        <Paper sx={{ p: 2 }}>
          <Typography variant="h6">{t("sarTitle")}</Typography>
          <TextField
            size="small"
            label={t("sarName")}
            value={sarName}
            onChange={(e) => setSarName(e.target.value)}
            fullWidth
            sx={{ mt: 1 }}
          />
          <TextField
            size="small"
            label={t("sarReason")}
            value={sarReason}
            onChange={(e) => setSarReason(e.target.value)}
            fullWidth
            sx={{ mt: 1 }}
          />
          <Button size="small" variant="contained" sx={{ mt: 1 }} onClick={createSar}>
            {t("createSar")}
          </Button>
          <Typography variant="subtitle2" sx={{ mt: 2 }}>
            {t("sarStatus")}
          </Typography>
          {sars.map((s) => (
            <Card variant="outlined" sx={{ mt: 1 }} key={s.id}>
              <CardContent>
                <Stack direction="row" justifyContent="space-between" alignItems="center">
                  <Typography variant="body2">
                    {s.id} · {s.name}
                  </Typography>
                  <Chip
                    size="small"
                    label={s.status}
                    color={s.status === "submitted" ? "success" : "default"}
                  />
                </Stack>
                <Typography variant="caption" color="text.secondary">
                  {s.reason}
                </Typography>
              </CardContent>
            </Card>
          ))}
        </Paper>
      </Grid>

      {/* 监管 MI 报表 */}
      <Grid item xs={12} md={4}>
        <Paper sx={{ p: 2 }}>
          <Typography variant="h6">{t("miTitle")}</Typography>
          {mi && (
            <Stack spacing={1} sx={{ mt: 1 }}>
              <Typography variant="body2">
                {t("miTotal")}：{mi.total_decisions}
              </Typography>
              <Typography variant="body2">
                {t("miHigh")}：{mi.high_risk_count}
              </Typography>
              <Typography variant="body2">
                {t("miAlerts")}：{mi.open_alerts}
              </Typography>
              <Typography variant="body2">
                {t("miSarTotal")}：{mi.sars_total}
              </Typography>
              <Typography variant="subtitle2" sx={{ mt: 1 }}>
                {t("miByVertical")}
              </Typography>
              {Object.entries(mi.by_vertical || {}).map(([k, v]) => (
                <Typography key={k} variant="caption" display="block">
                  {k}：{String(v)}
                </Typography>
              ))}
              <Typography variant="subtitle2" sx={{ mt: 1 }}>
                {t("miByAction")}
              </Typography>
              {Object.entries(mi.by_action || {}).map(([k, v]) => (
                <Typography key={k} variant="caption" display="block">
                  {k}：{String(v)}
                </Typography>
              ))}
              <Typography variant="caption" color="text.secondary" sx={{ mt: 1 }}>
                {t("generatedAt")}：{mi.generated_at}
              </Typography>
            </Stack>
          )}
        </Paper>
      </Grid>
    </Grid>
  );
}
