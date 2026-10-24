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
const ACTION_LABEL: Record<DecisionAction, string> = {
  approve: "通过",
  manual_review: "人工复核",
  reject: "驳回",
};
const STATUS_COLOR: Record<string, any> = {
  queued: "default",
  processing: "info",
  completed: "success",
  failed: "error",
};

export default function Home() {
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
        <Typography variant="h4">Ceron 控制台</Typography>
        <Chip
          label={`网关：${health?.status ?? "…"}`}
          color={health?.status === "ok" ? "success" : "default"}
        />
      </Stack>

      <Grid container spacing={2}>
        {/* 左：提交表单 */}
        <Grid item xs={12} md={5}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              文档提交
            </Typography>
            <FormControl fullWidth sx={{ mb: 2 }}>
              <InputLabel>垂直场景</InputLabel>
              <Select
                label="垂直场景"
                value={vertical}
                onChange={(e) => setVertical(e.target.value)}
              >
                <MenuItem value="insurance_hk">港股保险 / 承保理赔</MenuItem>
                <MenuItem value="family_office">家族办公室 KYC</MenuItem>
              </Select>
            </FormControl>
            <TextField
              label="文档文本"
              value={text}
              onChange={(e) => setText(e.target.value)}
              multiline
              minRows={8}
              fullWidth
              sx={{ mb: 1 }}
            />
            <Stack direction="row" spacing={1} sx={{ mb: 1 }}>
              <Button size="small" onClick={() => setText(SAMPLES[vertical])}>
                载入示例
              </Button>
            </Stack>
            <FormControlLabel
              control={<Checkbox checked={asyncMode} onChange={(e) => setAsyncMode(e.target.checked)} />}
              label="异步提交（看板轮询）"
            />
            <Box>
              <Button variant="contained" onClick={submit}>
                提交并编排
              </Button>
            </Box>
          </Paper>
        </Grid>

        {/* 右：审批看板 */}
        <Grid item xs={12} md={7}>
          <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 1 }}>
            <Typography variant="h6">作业看板</Typography>
            <FormControl size="small" sx={{ minWidth: 130 }}>
              <InputLabel>状态筛选</InputLabel>
              <Select
                label="状态筛选"
                value={statusFilter}
                onChange={(e) => {
                  setStatusFilter(e.target.value);
                  setPage(0);
                }}
              >
                <MenuItem value="">全部</MenuItem>
                <MenuItem value="queued">queued</MenuItem>
                <MenuItem value="processing">processing</MenuItem>
                <MenuItem value="completed">completed</MenuItem>
                <MenuItem value="failed">failed</MenuItem>
              </Select>
            </FormControl>
            <Button size="small" onClick={() => loadJobs()}>
              刷新
            </Button>
          </Stack>
          <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
            <Typography variant="caption" color="text.secondary">
              共 {total} 条
            </Typography>
            <Stack direction="row" spacing={1} alignItems="center">
              <Button size="small" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>
                上一页
              </Button>
              <Typography variant="caption">第 {page + 1} 页</Typography>
              <Button
                size="small"
                disabled={(page + 1) * PAGE_SIZE >= total}
                onClick={() => setPage((p) => p + 1)}
              >
                下一页
              </Button>
            </Stack>
          </Stack>
          <Grid container spacing={1}>
            {jobs.length === 0 && (
              <Typography variant="body2" color="text.secondary">
                暂无作业，提交后在此显示。
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
                          label={ACTION_LABEL[j.result.decision.action as DecisionAction]}
                          color={ACTION_COLOR[j.result.decision.action as DecisionAction]}
                        />
                      )}
                      {j.review_status && (
                        <Chip
                          size="small"
                          icon={j.review_status === "approved" ? <CheckCircleIcon /> : <CancelIcon />}
                          label={j.review_status === "approved" ? "已通过" : "已驳回"}
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
            <Typography variant="h6">处理结果 · {sel.id}</Typography>
            <Stack direction="row" spacing={1} alignItems="center">
              <TextField
                size="small"
                label="审批人"
                placeholder="manual"
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
                人工通过
              </Button>
              <Button
                size="small"
                variant="outlined"
                color="error"
                startIcon={<CancelIcon />}
                onClick={() => applyReview(sel.id, "rejected")}
                disabled={!!sel.review_status}
              >
                人工驳回
              </Button>
            </Stack>
          </Stack>
          {sel.review_status && (
            <Typography variant="caption" color="text.secondary">
              审批结论：{sel.review_status === "approved" ? "已通过" : "已驳回"} · 审批人：
              {sel.reviewed_by || "manual"}
              {sel.reviewed_at ? ` · 时间：${new Date(sel.reviewed_at).toLocaleString()}` : ""}
            </Typography>
          )}

          {!sel.result ? (
            <Typography sx={{ mt: 1 }} color="text.secondary">
              处理中（异步作业轮询中）…
            </Typography>
          ) : (
            <Grid container spacing={2} sx={{ mt: 0.5 }}>
              <Grid item xs={12} md={6}>
                <Typography variant="subtitle2">抽取字段</Typography>
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
                <Typography variant="subtitle2">富集结果</Typography>
                <Stack spacing={0.5} sx={{ mb: 1 }}>
                  <Typography variant="body2">数据源：{enrichment?.provider ?? "-"}</Typography>
                  <Typography variant="body2">
                    ICRIS 核验：{enrichment?.icris_verified ? "是" : "否"} · 制裁命中：
                    {enrichment?.sanctions_hit ? "是" : "否"} · 风险：{enrichment?.risk_from_enrich || "-"}
                  </Typography>
                  {(enrichment?.flags || []).map((f: string, i: number) => (
                    <Chip key={i} size="small" color="warning" label={f} sx={{ alignSelf: "flex-start" }} />
                  ))}
                </Stack>
                <Divider sx={{ my: 1 }} />
                <Typography variant="subtitle2">决策建议</Typography>
                {decision && (
                  <Stack spacing={0.5}>
                    <Chip
                      size="small"
                      label={ACTION_LABEL[decision.action as DecisionAction] || decision.action}
                      color={ACTION_COLOR[decision.action as DecisionAction] || "default"}
                    />
                    <Typography variant="body2">理由：{decision.reason}</Typography>
                    <Typography variant="body2">风险等级：{decision.risk_level}</Typography>
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
