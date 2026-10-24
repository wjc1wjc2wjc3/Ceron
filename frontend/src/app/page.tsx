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
import DescriptionIcon from "@mui/icons-material/Description";
import FactCheckIcon from "@mui/icons-material/FactCheck";
import NotificationsActiveIcon from "@mui/icons-material/NotificationsActive";
import GavelIcon from "@mui/icons-material/Gavel";
import SummarizeIcon from "@mui/icons-material/Summarize";
import HubIcon from "@mui/icons-material/Hub";
import Link from "next/link";
import { I18nProvider, LanguageSwitcher, useT } from "./i18n";
import MarketingNav from "../components/MarketingNav";
import SiteFooter from "../components/SiteFooter";

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

function Hero() {
  return (
    <Box sx={{ borderBottom: 1, borderColor: "divider" }}>
      <Box sx={{ maxWidth: 1180, mx: "auto", px: { xs: 2.5, md: 4 }, py: { xs: 8, md: 12 } }}>
        <Chip
          label="FROM APPLICATION TO AUDITABLE DECISION"
          size="small"
          sx={{ mb: 3, bgcolor: "#eef2ff", color: "#1f4dff", fontWeight: 700, letterSpacing: 1 }}
        />
        <Typography variant="h1" sx={{ mb: 3, maxWidth: 900 }}>
          Underwriting automation for Hong Kong finance
        </Typography>
        <Typography variant="h6" color="text.secondary" sx={{ maxWidth: 700, fontWeight: 400, mb: 5 }}>
          Ceron reads every submission — email, portal, WhatsApp or WeCom — enriches it against ICRIS,
          Land Registry, credit bureau and sanctions lists, then returns a decision-ready file with
          SFC / HKMA / MPFA compliance evidence attached.
        </Typography>
        <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
          <Button component={Link} href="/register" size="large" variant="contained">
            Start free
          </Button>
          <Button component={Link} href="/login" size="large" variant="outlined">
            Sign in to console
          </Button>
        </Stack>
        <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 3 }}>
          No credit card · Mock data sources included · Data residency in Hong Kong (PDPO)
        </Typography>
      </Box>
    </Box>
  );
}

function TrustRow() {
  return (
    <Box sx={{ borderBottom: 1, borderColor: "divider", bgcolor: "#fafbfd" }}>
      <Box sx={{ maxWidth: 1180, mx: "auto", px: { xs: 2.5, md: 4 }, py: 5 }}>
        <Typography variant="caption" sx={{ letterSpacing: 1.2, fontWeight: 700, color: "text.secondary" }}>
          BUILT FOR HONG KONG FINANCIAL INSTITUTIONS
        </Typography>
        <Stack direction="row" spacing={5} sx={{ mt: 3, flexWrap: "wrap", rowGap: 3 }}>
          {["Insurance & brokers", "Trusts", "Family offices", "Banks & MPF", "SFC-licensed asset managers"].map(
            (n) => (
              <Typography key={n} variant="subtitle1" fontWeight={700} color="text.secondary">
                {n}
              </Typography>
            )
          )}
        </Stack>
      </Box>
    </Box>
  );
}

function Stats() {
  const items = [
    { k: "8", v: "verticals with dedicated extraction schemas" },
    { k: "6", v: "external data sources behind one pluggable layer" },
    { k: "3", v: "languages across UI, extraction & decision rationale" },
  ];
  return (
    <Box sx={{ maxWidth: 1180, mx: "auto", px: { xs: 2.5, md: 4 }, py: { xs: 6, md: 9 } }}>
      <Grid container spacing={4}>
        {items.map((s) => (
          <Grid item xs={12} md={4} key={s.k}>
            <Typography variant="h2" color="primary.main" fontWeight={800}>
              {s.k}
            </Typography>
            <Typography variant="body1" color="text.secondary" sx={{ mt: 1 }}>
              {s.v}
            </Typography>
          </Grid>
        ))}
      </Grid>
    </Box>
  );
}

const STEPS = [
  {
    k: "INTAKE",
    t: "Emails come in as usual",
    d: "Forward to a mailbox, POST to our API, or let brokers use WhatsApp / WeCom. No behaviour change for your team.",
  },
  {
    k: "EXTRACT",
    t: "Bilingual documents get structured",
    d: "Traditional Chinese, English and simplified input parsed into vertical-specific fields with OCR + LLM.",
  },
  {
    k: "ENRICH",
    t: "Evidence is pulled from real sources",
    d: "ICRIS company search, Land Registry, credit bureau, OFAC / HMT sanctions, CRS / FATCA — fails safe to manual review.",
  },
  {
    k: "DECIDE",
    t: "A decision with reasons, not a score",
    d: "Approve / reject / escalate with a written rationale and every compliance gate recorded for the audit trail.",
  },
];

function HowItWorks() {
  return (
    <Box sx={{ bgcolor: "#fafbfd", borderTop: 1, borderBottom: 1, borderColor: "divider" }}>
      <Box sx={{ maxWidth: 1180, mx: "auto", px: { xs: 2.5, md: 4 }, py: { xs: 7, md: 10 } }}>
        <Typography variant="caption" sx={{ letterSpacing: 1.2, fontWeight: 700, color: "text.secondary" }}>
          HOW IT WORKS
        </Typography>
        <Typography variant="h2" sx={{ mt: 1, mb: 6, maxWidth: 720 }}>
          Four steps from raw submission to defensible decision
        </Typography>
        <Grid container spacing={3}>
          {STEPS.map((s, i) => (
            <Grid item xs={12} md={6} key={s.k}>
              <Paper variant="outlined" sx={{ p: 4, height: "100%" }}>
                <Stack direction="row" spacing={2} alignItems="center" sx={{ mb: 2 }}>
                  <Box
                    sx={{
                      width: 34, height: 34, borderRadius: "50%", bgcolor: "#eef2ff",
                      color: "#1f4dff", display: "grid", placeItems: "center", fontWeight: 800,
                    }}
                  >
                    {i + 1}
                  </Box>
                  <Typography variant="caption" fontWeight={700} color="text.secondary" sx={{ letterSpacing: 1 }}>
                    {s.k}
                  </Typography>
                </Stack>
                <Typography variant="h4" sx={{ mb: 1 }}>
                  {s.t}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {s.d}
                </Typography>
              </Paper>
            </Grid>
          ))}
        </Grid>
      </Box>
    </Box>
  );
}

const FEATURES = [
  {
    icon: <DescriptionIcon sx={{ color: "#1f4dff" }} />,
    t: "Document intelligence that handles Chinese",
    d: "Handles HK-specific artefacts — policy schedules, NAR1, trust deeds, MPF records — without template maintenance.",
  },
  {
    icon: <FactCheckIcon sx={{ color: "#1f4dff" }} />,
    t: "Compliance gates inside the pipeline",
    d: "SFC suitability, HKMA LTV / DSR, MPF contribution and OFC / LPF retail checks run before a decision is issued.",
  },
  {
    icon: <HubIcon sx={{ color: "#1f4dff" }} />,
    t: "One integration surface for data sources",
    d: "Swap a provider without touching your workflows. Every source degrades to manual review instead of breaking the run.",
  },
  {
    icon: <NotificationsActiveIcon sx={{ color: "#1f4dff" }} />,
    t: "Ongoing monitoring, not one-off checks",
    d: "Periodic sanctions re-screening and triggered re-KYC keep existing clients under continuous review.",
  },
  {
    icon: <GavelIcon sx={{ color: "#1f4dff" }} />,
    t: "SAR filing and regulatory MI",
    d: "Draft-to-submitted suspicious activity reports plus MI dashboards your compliance team can hand to regulators.",
  },
  {
    icon: <SummarizeIcon sx={{ color: "#1f4dff" }} />,
    t: "Every decision explained",
    d: "Field-level evidence, weighted reasons and trilingual rationale — built for model governance.",
  },
];

function Features() {
  return (
    <Box sx={{ maxWidth: 1180, mx: "auto", px: { xs: 2.5, md: 4 }, py: { xs: 7, md: 10 } }}>
      <Typography variant="caption" sx={{ letterSpacing: 1.2, fontWeight: 700, color: "text.secondary" }}>
        CAPABILITIES
      </Typography>
      <Typography variant="h2" sx={{ mt: 1, mb: 6, maxWidth: 760 }}>
        Everything a Hong Kong underwriting desk needs, out of the box
      </Typography>
      <Grid container spacing={3}>
        {FEATURES.map((f) => (
          <Grid item xs={12} md={4} key={f.t}>
            <Box>
              {f.icon}
              <Typography variant="h6" sx={{ mt: 1.5, mb: 0.5 }}>
                {f.t}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {f.d}
              </Typography>
            </Box>
          </Grid>
        ))}
      </Grid>
    </Box>
  );
}

function QuoteSection() {
  return (
    <Box sx={{ bgcolor: "#0b1a3a", color: "#fff" }}>
      <Box sx={{ maxWidth: 1180, mx: "auto", px: { xs: 2.5, md: 4 }, py: { xs: 7, md: 10 } }}>
        <Typography variant="h3" sx={{ maxWidth: 880, mb: 3, lineHeight: 1.4 }}>
          “We want evidence on every decision. Ceron sits at the top of our funnel because it handles
          the most important data first.”
        </Typography>
        <Typography variant="body2" sx={{ opacity: 0.8 }}>
          Head of Operations · Hong Kong family office
        </Typography>
      </Box>
    </Box>
  );
}

function FinalCta() {
  return (
    <Box sx={{ borderTop: 1, borderColor: "divider" }}>
      <Box sx={{ maxWidth: 1180, mx: "auto", px: { xs: 2.5, md: 4 }, py: { xs: 7, md: 10 }, textAlign: "center" }}>
        <Typography variant="caption" sx={{ letterSpacing: 1.2, fontWeight: 700, color: "text.secondary" }}>
          GET STARTED IN MINUTES
        </Typography>
        <Typography variant="h2" sx={{ mt: 1, mb: 4 }}>
          See a submission become a decision
        </Typography>
        <Stack direction={{ xs: "column", sm: "row" }} spacing={2} justifyContent="center">
          <Button component={Link} href="/register" size="large" variant="contained">
            Create free account
          </Button>
          <Button component={Link} href="/products" size="large" variant="outlined">
            Tour the platform
          </Button>
        </Stack>
      </Box>
    </Box>
  );
}

export default function Home() {
  return (
    <I18nProvider>
      <MarketingNav />
      <Hero />
      <TrustRow />
      <Stats />
      <HowItWorks />
      <Features />
      <QuoteSection />
      <FinalCta />
      <SiteFooter />
    </I18nProvider>
  );
}// 承保工作台：被营销首页下方的 demo 区与受保护的 /app 控制台共用，故导出。
export function JobsView() {
  const { t, locale } = useT();
  const [health, setHealth] = useState<any>(null);
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

