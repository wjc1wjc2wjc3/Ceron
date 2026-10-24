"use client";

import { useEffect, useRef, useState } from "react";
import {
  Box, Button, Card, CardContent, Chip, Divider, FormControl,
  FormControlLabel, Grid, InputLabel, MenuItem, Paper, Select,
  Stack, Table, TableBody, TableCell, TableRow, TextField, Typography,
  Checkbox,
} from "@mui/material";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import CancelIcon from "@mui/icons-material/Cancel";
import { I18nProvider, LanguageSwitcher, useT } from "./i18n";

type DecisionAction = "approve" | "manual_review" | "reject";

interface Job {
  id: string;
  vertical: string;
  status: string;
  result: any | null;
  review_status?: string;
  review_note?: string;
  reviewed_by?: string;
  reviewed_at?: string;
  created_at?: string;
  submittedAt?: number;
}

const PAGE_SIZE = 10;

const SAMPLES: Record<string, string> = {
  insurance_hk:
    "投保人：香港環宇保險有限公司\n保單號：HK12345\n受保人：張三\n險種：終身壽險\n保額：800萬\n年繳保費：20萬\n理賠類型：身故\n理賠金額：120萬\n資料完整度：0.9",
  family_office:
    "客戶姓名：陳大文家族辦公室有限公司\n身份類型：公司（家族辦公室）\n資產規模：50,000萬港元\n資金來源：家族持股出售所得\n受益所有人：陳大文\n風險等級：中\nKYC狀態：待補",
};

const ACTION_COLOR: Record<DecisionAction, "success" | "warning" | "error"> = {
  approve: "success",
  manual_review: "warning",
  reject: "error",
};
const STATUS_COLOR: Record<string, any> = {
  queued: "default",
  processing: "info",
  completed: "success",
  failed: "error",
};

function actionLabel(t: (k: string) => string, action: string): string {
  if (action === "approve") return t("approve");
  if (action === "rejected") return t("reject");
  return t("manual_review");
}

export default function Home() {
  return (
    <I18nProvider>
      <Dashboard />
    </I18nProvider>
  );
}

function Dashboard() {
  const { t } = useT();
  const [health, setHealth] = useState<any>(null);
  const [vertical, setVertical] = useState("insurance_hk");
  const [text, setText] = useState(SAMPLES.insurance_hk);
  const [asyncMode, setAsyncMode] = useState(false);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState("");
  const [page, setPage] = useState(0);
  const [total, setTotal] = useState(0);
  const [reviewer, setReviewer] = useState("");
  const timers = useRef<Record<string, any>>({});

  async function loadJobs(f = statusFilter, p = page) {
    const params = new URLSearchParams({
      limit: String(PAGE_SIZE),
      offset: String(p * PAGE_SIZE),
    });
    if (f) params.set("status", f);
    const res = await fetch(`/api/v1/jobs?${params.toString()}`);
    if (!res.ok) return;
    const data = await res.json();
    setJobs(data.jobs || []);
    setTotal(data.count || 0);
  }

  useEffect(() => {
    fetch("/api/health")
      .then((r) => r.json())
      .then(setHealth)
      .catch(() => setHealth({ status: "error" }));
    return () => {
      Object.values(timers.current).forEach(clearInterval);
    };
  }, []);

  useEffect(() => {
    loadJobs(statusFilter, page);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter, page]);

  const loadRef = useRef(loadJobs);
  useEffect(() => {
    loadRef.current = loadJobs;
  });
  useEffect(() => {
    const t = setInterval(() => loadRef.current(), 5000); // 周期刷新：异步状态/多端同步
    return () => clearInterval(t);
  }, []);

  async function submit() {
    const body = JSON.stringify({ vertical, text });
    const url = asyncMode ? "/api/v1/intake/async" : "/api/v1/intake";
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
    });
    const job = await res.json();
    setSelected(job.id);
    setPage(0);
    await loadJobs(statusFilter, 0);
    if (asyncMode) poll(job.id);
  }

  function poll(id: string) {
    timers.current[id] = setInterval(async () => {
      const res = await fetch(`/api/v1/jobs/${id}`);
      if (!res.ok) return;
      const job = await res.json();
      setJobs((j) =>
        j.map((x) => (x.id === id ? { ...x, status: job.status, result: job.result } : x))
      );
      if (job.status === "completed" || job.status === "failed") {
        clearInterval(timers.current[id]);
        delete timers.current[id];
      }
    }, 800);
  }

  async function applyReview(id: string, status: "approved" | "rejected") {
    const res = await fetch(`/api/v1/jobs/${id}/review`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status, reviewer }),
    });
    if (!res.ok) return;
    const job = await res.json();
    setJobs((j) =>
      j.map((x) =>
        x.id === id
          ? {
              ...x,
              review_status: job.review_status,
              review_note: job.review_note,
              reviewed_by: job.reviewed_by,
              reviewed_at: job.reviewed_at,
            }
          : x
      )
    );
  }

  const sel = jobs.find((j) => j.id === selected) || null;
  const decision: any = sel?.result?.decision;
  const enrichment: any = sel?.result?.enrichment;
  const extracted: Record<string, any> = sel?.result?.extracted || {};

  return (
    <Box sx={{ p: 3, maxWidth: 1200, mx: "auto" }}>
      <Stack direction="row" alignItems="center" spacing={2} sx={{ mb: 2 }}>
        <Typography variant="h4">{t("appTitle")}</Typography>
        <Chip
          label={`${t("gateway")}：${health?.status ?? "…"}`}
          color={health?.status === "ok" ? "success" : "default"}
        />
        <Box sx={{ flexGrow: 1 }} />
        <LanguageSwitcher />
      </Stack>

      <Grid container spacing={2}>
        {/* 左：提交表单 */}
        <Grid item xs={12} md={5}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              {t("submitTitle")}
            </Typography>
            <FormControl fullWidth sx={{ mb: 2 }}>
              <InputLabel>{t("vertical")}</InputLabel>
              <Select
                label={t("vertical")}
                value={vertical}
                onChange={(e) => setVertical(e.target.value)}
              >
                <MenuItem value="insurance_hk">{t("v.insurance_hk")}</MenuItem>
                <MenuItem value="family_office">{t("v.family_office")}</MenuItem>
              </Select>
            </FormControl>
            <TextField
              label={t("docText")}
              value={text}
              onChange={(e) => setText(e.target.value)}
              multiline
              minRows={8}
              fullWidth
              sx={{ mb: 1 }}
            />
            <Stack direction="row" spacing={1} sx={{ mb: 1 }}>
              <Button size="small" onClick={() => setText(SAMPLES[vertical])}>
                {t("loadSample")}
              </Button>
            </Stack>
            <FormControlLabel
              control={<Checkbox checked={asyncMode} onChange={(e) => setAsyncMode(e.target.checked)} />}
              label={t("asyncMode")}
            />
            <Box>
              <Button variant="contained" onClick={submit}>
                {t("submit")}
              </Button>
            </Box>
          </Paper>
        </Grid>

        {/* 右：审批看板 */}
        <Grid item xs={12} md={7}>
          <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 1 }}>
            <Typography variant="h6">{t("kanban")}</Typography>
            <FormControl size="small" sx={{ minWidth: 130 }}>
              <InputLabel>{t("statusFilter")}</InputLabel>
              <Select
                label={t("statusFilter")}
                value={statusFilter}
                onChange={(e) => {
                  setStatusFilter(e.target.value);
                  setPage(0);
                }}
              >
                <MenuItem value="">{t("status.all")}</MenuItem>
                <MenuItem value="queued">{t("status.queued")}</MenuItem>
                <MenuItem value="processing">{t("status.processing")}</MenuItem>
                <MenuItem value="completed">{t("status.completed")}</MenuItem>
                <MenuItem value="failed">{t("status.failed")}</MenuItem>
              </Select>
            </FormControl>
            <Button size="small" onClick={() => loadJobs()}>
              {t("refresh")}
            </Button>
          </Stack>
          <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
            <Typography variant="caption" color="text.secondary">
              {t("total").replace("{n}", String(total))}
            </Typography>
            <Stack direction="row" spacing={1} alignItems="center">
              <Button size="small" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>
                {t("prev")}
              </Button>
              <Typography variant="caption">{t("page").replace("{n}", String(page + 1))}</Typography>
              <Button
                size="small"
                disabled={(page + 1) * PAGE_SIZE >= total}
                onClick={() => setPage((p) => p + 1)}
              >
                {t("next")}
              </Button>
            </Stack>
          </Stack>
          <Grid container spacing={1}>
            {jobs.length === 0 && (
              <Typography variant="body2" color="text.secondary">
                {t("empty")}
              </Typography>
            )}
            {jobs.map((j) => (
              <Grid item xs={12} sm={6} key={j.id}>
                <Card
                  variant="outlined"
                  sx={{ cursor: "pointer", borderColor: selected === j.id ? "primary.main" : undefined }}
                  onClick={() => setSelected(j.id)}
                >
                  <CardContent>
                    <Stack direction="row" justifyContent="space-between" alignItems="center">
                      <Typography variant="body2" noWrap sx={{ maxWidth: 160 }}>
                        {j.id}
                      </Typography>
                      <Chip size="small" label={j.status} color={STATUS_COLOR[j.status] || "default"} />
                    </Stack>
                    <Stack direction="row" spacing={1} sx={{ mt: 1 }} alignItems="center">
                      <Chip size="small" label={j.vertical} variant="outlined" />
                      {j.result?.decision?.action && (
                        <Chip
                          size="small"
                          label={actionLabel(t, j.result.decision.action)}
                          color={ACTION_COLOR[j.result.decision.action as DecisionAction]}
                        />
                      )}
                      {j.review_status && (
                        <Chip
                          size="small"
                          icon={j.review_status === "approved" ? <CheckCircleIcon /> : <CancelIcon />}
                          label={j.review_status === "approved" ? t("approved") : t("rejected")}
                          color={j.review_status === "approved" ? "success" : "error"}
                        />
                      )}
                    </Stack>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        </Grid>
      </Grid>

      {/* 结果展示 */}
      {sel && (
        <Paper sx={{ p: 2, mt: 2 }}>
          <Stack direction="row" justifyContent="space-between" alignItems="center">
            <Typography variant="h6">
              {t("resultTitle")} · {sel.id}
            </Typography>
            <Stack direction="row" spacing={1} alignItems="center">
              <TextField
                size="small"
                label={t("reviewer")}
                placeholder={t("manual")}
                value={reviewer}
                onChange={(e) => setReviewer(e.target.value)}
                sx={{ width: 140 }}
              />
              <Button
                size="small"
                variant="outlined"
                color="success"
                startIcon={<CheckCircleIcon />}
                onClick={() => applyReview(sel.id, "approved")}
                disabled={!!sel.review_status}
              >
                {t("manualApprove")}
              </Button>
              <Button
                size="small"
                variant="outlined"
                color="error"
                startIcon={<CancelIcon />}
                onClick={() => applyReview(sel.id, "rejected")}
                disabled={!!sel.review_status}
              >
                {t("manualReject")}
              </Button>
            </Stack>
          </Stack>
          {sel.review_status && (
            <Typography variant="caption" color="text.secondary">
              {t("reviewConclusion")
                .replace("{status}", sel.review_status === "approved" ? t("approved") : t("rejected"))
                .replace("{by}", sel.reviewed_by || t("manual"))
                .replace(
                  "{at}",
                  sel.reviewed_at ? ` · ${t("timePrefix")}${new Date(sel.reviewed_at).toLocaleString()}` : ""
                )}
            </Typography>
          )}

          {!sel.result ? (
            <Typography sx={{ mt: 1 }} color="text.secondary">
              {t("processing")}
            </Typography>
          ) : (
            <Grid container spacing={2} sx={{ mt: 0.5 }}>
              <Grid item xs={12} md={6}>
                <Typography variant="subtitle2">{t("extracted")}</Typography>
                <Table size="small">
                  <TableBody>
                    {Object.entries(extracted).map(([k, v]) => (
                      <TableRow key={k}>
                        <TableCell sx={{ fontWeight: 600, width: "45%" }}>{k}</TableCell>
                        <TableCell>{String(v)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </Grid>
              <Grid item xs={12} md={6}>
                <Typography variant="subtitle2">{t("enrichment")}</Typography>
                <Stack spacing={0.5} sx={{ mb: 1 }}>
                  <Typography variant="body2">
                    {t("dataSource")}
                    {enrichment?.provider ?? "-"}
                  </Typography>
                  <Typography variant="body2">
                    {t("icris")}
                    {enrichment?.icris_verified ? t("yes") : t("no")} · {t("sanctions")}
                    {enrichment?.sanctions_hit ? t("yes") : t("no")} · {t("risk")}
                    {enrichment?.risk_from_enrich || "-"}
                  </Typography>
                  {(enrichment?.flags || []).map((f: string, i: number) => (
                    <Chip key={i} size="small" color="warning" label={f} sx={{ alignSelf: "flex-start" }} />
                  ))}
                </Stack>
                <Divider sx={{ my: 1 }} />
                <Typography variant="subtitle2">{t("decision")}</Typography>
                {decision && (
                  <Stack spacing={0.5}>
                    <Chip
                      size="small"
                      label={actionLabel(t, decision.action) || decision.action}
                      color={ACTION_COLOR[decision.action as DecisionAction] || "default"}
                    />
                    <Typography variant="body2">
                      {t("reason")}
                      {decision.reason}
                    </Typography>
                    <Typography variant="body2">
                      {t("riskLevel")}
                      {decision.risk_level}
                    </Typography>
                  </Stack>
                )}
              </Grid>
            </Grid>
          )}
        </Paper>
      )}
    </Box>
  );
}
