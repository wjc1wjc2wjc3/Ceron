"use client";

import { useEffect, useRef, useState } from "react";
import {
  Box, Button, Card, CardContent, Checkbox, Chip, Divider, FormControl,
  FormControlLabel, Grid, InputLabel, MenuItem, Paper, Select, Stack,
  Table, TableBody, TableCell, TableRow, TextField, Typography,
} from "@mui/material";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import CancelIcon from "@mui/icons-material/Cancel";
import DownloadIcon from "@mui/icons-material/Download";
import { useT } from "../app/i18n";

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

// 範例文本按 locale 本地化，避免简体界面混入繁体示例。
const SAMPLES: Record<string, Record<string, string>> = {
  "zh-HK": {
    insurance_hk:
      "投保人：香港環宇保險有限公司\n保單號：HK12345\n受保人：張三\n險種：終身壽險\n保額：800萬\n年繳保費：20萬\n理賠類型：身故\n理賠金額：120萬\n資料完整度：0.9",
    family_office:
      "客戶姓名：陳大文家族辦公室有限公司\n身份類型：公司（家族辦公室）\n資產規模：50,000萬港元\n資金來源：家族持股出售所得\n受益所有人：陳大文\n風險等級：中\nKYC狀態：待補",
    banking_mortgage:
      "申請人：李小明\n物業估值：1,000萬\n貸款金額：700萬\n貸款成數LTV：0.7\n月收入：8萬\n月負債供款：5萬\n供款入息比率DSR：0.62\n物業類型：住宅\n首期資金來源：儲蓄\nKYC狀態：完成",
    securities_suitability:
      "客戶姓名：王五\n風險承受度：低\n產品風險等級：高\n投資經驗年：1\n財務狀況：200萬\n投資知識水平：低\n產品類型：衍生品\nKYC狀態：完成",
    mpf:
      "成員姓名：陳六\n計劃類型：強積金\n僱主名稱：某某有限公司\n僱員狀態：在職\n僱主登記狀態：未登記\n供款狀態：正常\n自願供款：無\nKYC狀態：完成",
    fund_ofc_lpf:
      "基金名稱：環宇機會基金\n結構類型：OFC\n是否獲證監會認可：否\n管理公司：環宇資產管理\n投資者類型：零售\n受益所有人：張三\n募資規模：5,000萬\nKYC狀態：完成",
  },
  en: {
    insurance_hk:
      "Policyholder: Hong Kong Universal Insurance Ltd\nPolicy No: HK12345\nInsured: Zhang San\nProduct: Whole Life\nSum Assured: 8,000,000\nAnnual Premium: 200,000\nClaim Type: Death\nClaim Amount: 1,200,000\nCompleteness: 0.9",
    family_office:
      "Client: Chan Tai Man Family Office Ltd\nEntity Type: Company (Family Office)\nAssets: 500,000,000 HKD\nSource of Funds: proceeds from sale of family shareholding\nBeneficial Owner: Chan Tai Man\nRisk Level: Medium\nKYC Status: Pending",
    banking_mortgage:
      "Applicant: Li Si\nProperty Valuation: 10,000,000\nLoan Amount: 7,000,000\nLTV: 0.7\nMonthly Income: 80,000\nMonthly Debt Servicing: 50,000\nDSR: 0.62\nProperty Type: Residential\nDown-payment Source: savings\nKYC Status: Completed",
    securities_suitability:
      "Client: Wang Wu\nRisk Tolerance: Low\nProduct Risk: High\nInvestment Experience (yrs): 1\nFinancial Situation: 2,000,000\nKnowledge Level: Low\nProduct Type: Derivatives\nKYC Status: Completed",
    mpf:
      "Member: Chen Liu\nScheme: MPF\nEmployer: Some Ltd\nEmployment: Employed\nEmployer Registration: Not Registered\nContribution: Normal\nVoluntary: None\nKYC Status: Completed",
    fund_ofc_lpf:
      "Fund: Universal Opportunity Fund\nStructure: OFC\nSFC Authorized: No\nManager: Universal Asset Management\nInvestor Type: Retail\nBeneficial Owner: Zhang San\nRaise: 50,000,000\nKYC Status: Completed",
  },
  "zh-CN": {
    insurance_hk:
      "投保人：香港环宇保险有限公司\n保单号：HK12345\n受保人：张三\n险种：终身寿险\n保额：800万\n年缴保费：20万\n理赔类型：身故\n理赔金额：120万\n资料完整度：0.9",
    family_office:
      "客户姓名：陈大文家族办公室有限公司\n身份类型：公司（家族办公室）\n资产规模：500,000万港元\n资金来源：家族持股出售所得\n受益所有人：陈大文\n风险等级：中\nKYC状态：待补",
    banking_mortgage:
      "申请人：李四\n物业估值：1,000万\n贷款金额：700万\n贷款成数LTV：0.7\n月收入：8万\n月负债供款：5万\n供款入息比率DSR：0.62\n物业类型：住宅\n首期资金来源：储蓄\nKYC状态：完成",
    securities_suitability:
      "客户姓名：王五\n风险承受度：低\n产品风险等级：高\n投资经验年：1\n财务状况：200万\n投资知识水平：低\n产品类型：衍生品\nKYC状态：完成",
    mpf:
      "成员姓名：陈六\n计划类型：强积金\n雇主名称：某某有限公司\n雇员状态：在职\n雇主登记状态：未登记\n供款状态：正常\n自愿供款：无\nKYC状态：完成",
    fund_ofc_lpf:
      "基金名称：环宇机会基金\n结构类型：OFC\n是否获证监会认可：否\n管理公司：环宇资产管理\n投资者类型：零售\n受益所有人：张三\n募资规模：5000万\nKYC状态：完成",
  },
};

const sampleFor = (loc: string, vertical: string): string => {
  const byLoc = SAMPLES[loc] || SAMPLES["zh-HK"];
  return byLoc[vertical] ?? byLoc.insurance_hk;
};

// 判断当前文本是否仍是某个内置示例（是则可随语言/业务线自动切换，否则不打扰用户输入）。
const isSampleText = (s: string): boolean =>
  Object.values(SAMPLES).some((byLoc) => Object.values(byLoc).includes(s));

const ACTION_COLOR: Record<DecisionAction, "success" | "warning" | "error"> = {
  approve: "success",
  manual_review: "warning",
  reject: "error",
};
// HITL 级别 → i18n key
const REVIEW_LABEL: Record<string, string> = {
  none: "reviewNone",
  field: "reviewField",
  source: "reviewSource",
  gate: "reviewGate",
  risk: "reviewRisk",
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

// 承保工作台：受保护的 /app 控制台与营销页共用同一实现。
export default function JobsView() {
  const { t, locale } = useT();
  const [vertical, setVertical] = useState("insurance_hk");
  const [text, setText] = useState(sampleFor("zh-HK", "insurance_hk"));
  const [asyncMode, setAsyncMode] = useState(false);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState("");
  const [page, setPage] = useState(0);
  const [total, setTotal] = useState(0);

  // 切换语言 / 业务线时，若文本框仍是内置示例，则自动换成对应语言、对应业务线的示例。
  useEffect(() => {
    setText((cur) => (isSampleText(cur) ? sampleFor(locale, vertical) : cur));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [locale, vertical]);
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
    const id = setInterval(() => loadRef.current(), 5000); // 周期刷新：异步状态/多端同步
    return () => clearInterval(id);
  }, []);

  async function submit() {
    const body = JSON.stringify({ vertical, text, locale });
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

  // 审计包：一次性作业的证据链（抽取字段 / 富集信号 / 规则命中 / trace），可交给合规与监管
  async function downloadAudit(runId?: string) {
    if (!runId) return;
    const res = await fetch(`/py/v1/runs/${runId}/audit`);
    if (!res.ok) return;
    const pack = await res.json();
    const blob = new Blob([JSON.stringify(pack, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `ceron-audit-${runId}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  const sel = jobs.find((j) => j.id === selected) || null;
  const decision: any = sel?.result?.decision;
  const enrichment: any = sel?.result?.enrichment;
  const extracted: Record<string, any> = sel?.result?.extracted || {};

  return (
    <Box sx={{ p: 3, maxWidth: 1200, mx: "auto" }}>
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
                <MenuItem value="banking_mortgage">{t("v.banking_mortgage")}</MenuItem>
                <MenuItem value="securities_suitability">{t("v.securities_suitability")}</MenuItem>
                <MenuItem value="mpf">{t("v.mpf")}</MenuItem>
                <MenuItem value="fund_ofc_lpf">{t("v.fund_ofc_lpf")}</MenuItem>
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
              <Button size="small" onClick={() => setText(sampleFor(locale, vertical))}>
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
                      <Chip size="small" label={t("status." + j.status)} color={STATUS_COLOR[j.status] || "default"} />
                    </Stack>
                    <Stack direction="row" spacing={1} sx={{ mt: 1 }} alignItems="center">
                      <Chip size="small" label={t("v." + j.vertical)} variant="outlined" />
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
              <Button
                size="small"
                variant="outlined"
                startIcon={<DownloadIcon />}
                disabled={!sel.result?.run_id}
                onClick={() => downloadAudit(sel.result?.run_id)}
                title={sel.result?.run_id ? t("auditDownload") : t("auditNoRun")}
              >
                {t("auditDownload")}
              </Button>
            </Stack>
          </Stack>

          {/* 人工覆核分级（HITL 检查点）+ 命中的合规规则：让「为什么喊人」可见 */}
          {sel.result?.decision?.review && (
            <Stack direction="row" spacing={1} sx={{ mt: 1.5 }} alignItems="center" flexWrap="wrap" rowGap={1}>
              <Chip
                size="small"
                color={
                  sel.result.decision.review.level === "none"
                    ? "default"
                    : sel.result.decision.review.level === "risk"
                    ? "error"
                    : "warning"
                }
                label={`${t("reviewLevel")}：${t(
                  REVIEW_LABEL[String(sel.result.decision.review.level)] || "reviewNone"
                )}`}
              />
              {sel.result.decision.rule_pack?.version && (
                <Chip size="small" variant="outlined" label={`rule pack ${sel.result.decision.rule_pack.version}`} />
              )}
              {!!sel.result.trace_summary?.steps && (
                <Chip size="small" variant="outlined" label={`${t("traceSteps")} ${sel.result.trace_summary.steps}`} />
              )}
            </Stack>
          )}
          {!!(sel.result?.decision?.rules_hit || []).length && (
            <Box sx={{ mt: 1.5 }}>
              <Typography variant="caption" color="text.secondary">
                {t("rulesHitTitle")}
              </Typography>
              <Stack direction="row" spacing={1} sx={{ mt: 0.5 }} flexWrap="wrap" rowGap={1}>
                {(sel.result.decision.rules_hit as any[]).map((h: any) => (
                  <Chip
                    key={h.id}
                    size="small"
                    variant="outlined"
                    color={h.severity === "critical" ? "error" : h.severity === "high" ? "warning" : "default"}
                    label={`${h.gate} · ${h.id} (+${h.delta})`}
                    title={h.reason}
                  />
                ))}
              </Stack>
            </Box>
          )}
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
                    {enrichment?.sanctions_hit ? t("yes") : t("no")} ·                     {t("risk")}
                    {enrichment?.risk_from_enrich === "high"
                      ? t("riskHigh")
                      : enrichment?.risk_from_enrich === "normal"
                      ? t("riskNormal")
                      : (enrichment?.risk_from_enrich || "-")}
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
                      {Array.isArray(decision.reasons)
                        ? decision.reasons.join("；")
                        : String(decision.reasons ?? "")}
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
