"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { FormControl, InputLabel, MenuItem, Select } from "@mui/material";

export type Locale = "zh-HK" | "en" | "zh-CN";

// 平台面向香港金融机构，内置 繁體中文 / English / 简体中文 三语切换（持久化于 localStorage）。
const dict: Record<Locale, Record<string, string>> = {
  "zh-HK": {
    appTitle: "Ceron 控制台",
    gateway: "網關",
    submitTitle: "文件提交",
    vertical: "垂直場景",
    "v.insurance_hk": "港股保險 / 承保理賠",
    "v.family_office": "家族辦公室 KYC",
    "v.banking_mortgage": "銀行按揭承保",
    "v.securities_suitability": "證券合適性",
    "v.mpf": "強積金 MPF",
    "v.fund_ofc_lpf": "基金 / OFC / LPF",
    docText: "文件文本",
    loadSample: "載入範例",
    asyncMode: "非同步提交（看板輪詢）",
    submit: "提交並編排",
    kanban: "作業看板",
    statusFilter: "狀態篩選",
    "status.all": "全部",
    "status.queued": "排隊中",
    "status.processing": "處理中",
    "status.completed": "已完成",
    "status.failed": "失敗",
    refresh: "重新整理",
    total: "共 {n} 條",
    prev: "上一頁",
    next: "下一頁",
    page: "第 {n} 頁",
    empty: "暫無作業，提交後在此顯示。",
    resultTitle: "處理結果",
    reviewer: "審批人",
    approve: "通過",
    manual_review: "人工複核",
    reject: "駁回",
    approved: "已通過",
    rejected: "已駁回",
    manualApprove: "人工通過",
    manualReject: "人工駁回",
    reviewConclusion: "審批結論：{status} · 審批人：{by}{at}",
    manual: "手動",
    timePrefix: "時間：",
    processing: "處理中（非同步作業輪詢中）…",
    extracted: "抽取欄位",
    enrichment: "富集結果",
    dataSource: "資料來源：",
    icris: "ICRIS 核驗：",
    sanctions: "制裁命中：",
    risk: "風險：",
    decision: "決策建議",
    reason: "理由：",
    riskLevel: "風險等級：",
    yes: "是",
    no: "否",
    riskHigh: "高",
    riskNormal: "正常",
    navWorkspace: "工作台",
    navCompliance: "合規運營",
    navProducts: "產品能力",
    productsTitle: "Ceron 產品能力",
    productsSubtitle: "面向香港金融業的承保與合規自動化：從多入口收件到可審計決策、持續監控與監管申報。",
    pgUnderwriting: "承保與理賠",
    pgCompliance: "合規運營",
    pgData: "數據與集成",
    pExtractName: "文檔智能抽取",
    pExtractDesc: "繁中/英雙語 OCR + LLM 結構化抽取，8 條業務線專屬字段模板。",
    pDecisionName: "決策引擎",
    pDecisionDesc: "風險評分 + SFC/HKMA/MPFA 合規閘口，輸出通過/拒絕/轉人工及三語理由。",
    pKanbanName: "作業看板與審批",
    pKanbanDesc: "異步流水線、狀態篩選與分頁、審批留痕審計。",
    pMonitorName: "持續監控",
    pMonitorDesc: "制裁/OFAC/HMT 名單週期重查、觸發式 re-KYC，命中自動告警。",
    pSarName: "SAR 申報",
    pSarDesc: "可疑交易申報（JFIU）草稿→提交狀態機與留痕。",
    pMiName: "監管 MI 報表",
    pMiDesc: "決策/告警/SAR 聚合，按業務線與結論穿透。",
    pEnrichName: "數據富集",
    pEnrichDesc: "ICRIS/土地註冊/信貸局/OFAC/HMT/CRS 8 源可插拔，失敗自動降級人工複核。",
    pIntakeName: "多入口收件",
    pIntakeDesc: "API / WhatsApp Business / 企業微信統一接入與異步編排。",
    pSyncName: "CRM 同步",
    pSyncDesc: "結構化結果 + 審計追蹤同步 Salesforce/Dynamics（建設中）。",
    statusLive: "已上線",
    statusPlanned: "建設中",
    tabCompliance: "合規運營",
    monitoring: "持續監控",
    scanNow: "立即重查",
    alerts: "監控告警",
    noAlerts: "暫無告警。",
    sarTitle: "可疑交易申報 (SAR)",
    createSar: "生成 SAR",
    sarName: "實體名稱",
    sarReason: "申報理由",
    sarStatus: "狀態",
    sarSubmitted: "已提交",
    miTitle: "監管 MI 報表",
    miTotal: "決策總數",
    miHigh: "高風險數",
    miByVertical: "按業務線",
    miByAction: "按結論",
    miAlerts: "未結告警",
    miSarTotal: "SAR 總數",
    generatedAt: "生成時間",
  },
  en: {
    appTitle: "Ceron Console",
    gateway: "Gateway",
    submitTitle: "Document Intake",
    vertical: "Vertical",
    "v.insurance_hk": "HK Equity Insurance / Underwriting",
    "v.family_office": "Family Office KYC",
    "v.banking_mortgage": "Bank Mortgage Underwriting",
    "v.securities_suitability": "Securities Suitability",
    "v.mpf": "MPF",
    "v.fund_ofc_lpf": "Fund / OFC / LPF",
    docText: "Document Text",
    loadSample: "Load Sample",
    asyncMode: "Async submit (kanban polling)",
    submit: "Submit & Orchestrate",
    kanban: "Job Kanban",
    statusFilter: "Status Filter",
    "status.all": "All",
    "status.queued": "Queued",
    "status.processing": "Processing",
    "status.completed": "Completed",
    "status.failed": "Failed",
    refresh: "Refresh",
    total: "{n} total",
    prev: "Prev",
    next: "Next",
    page: "Page {n}",
    empty: "No jobs yet. Submit to populate.",
    resultTitle: "Processing Result",
    reviewer: "Reviewer",
    approve: "Approve",
    manual_review: "Manual Review",
    reject: "Reject",
    approved: "Approved",
    rejected: "Rejected",
    manualApprove: "Approve",
    manualReject: "Reject",
    reviewConclusion: "Review: {status} · Reviewer: {by}{at}",
    manual: "manual",
    timePrefix: "Time: ",
    processing: "Processing (polling async job)…",
    extracted: "Extracted Fields",
    enrichment: "Enrichment",
    dataSource: "Source: ",
    icris: "ICRIS verified: ",
    sanctions: "Sanctions hit: ",
    risk: "Risk: ",
    decision: "Decision",
    reason: "Reason: ",
    riskLevel: "Risk level: ",
    yes: "Yes",
    no: "No",
    riskHigh: "High",
    riskNormal: "Normal",
    navWorkspace: "Workspace",
    navCompliance: "Compliance Ops",
    navProducts: "Products",
    productsTitle: "Ceron Products",
    productsSubtitle: "Underwriting & compliance automation for Hong Kong finance: from multi-channel intake to auditable decisions, ongoing monitoring and regulatory reporting.",
    pgUnderwriting: "Underwriting & Claims",
    pgCompliance: "Compliance Operations",
    pgData: "Data & Integration",
    pExtractName: "Intelligent Extraction",
    pExtractDesc: "Bilingual (TC/EN) OCR + LLM structured extraction with per-vertical field templates.",
    pDecisionName: "Decision Engine",
    pDecisionDesc: "Risk scoring + SFC/HKMA/MPFA compliance gates with trilingual rationale.",
    pKanbanName: "Job Kanban & Review",
    pKanbanDesc: "Async pipeline, status filters & pagination, review audit trail.",
    pMonitorName: "Ongoing Monitoring",
    pMonitorDesc: "Periodic sanctions/OFAC/HMT re-screening with triggered re-KYC and alerting.",
    pSarName: "SAR Filing",
    pSarDesc: "Suspicious activity reports (JFIU) with draft-to-submitted workflow.",
    pMiName: "Regulatory MI",
    pMiDesc: "Aggregated decision/alert/SAR reporting by vertical and action.",
    pEnrichName: "Data Enrichment",
    pEnrichDesc: "8 pluggable sources: ICRIS, Land Search, credit bureau, OFAC/HMT, CRS with auto-degrade.",
    pIntakeName: "Multi-channel Intake",
    pIntakeDesc: "API / WhatsApp Business / WeCom unified intake with async orchestration.",
    pSyncName: "CRM Sync",
    pSyncDesc: "Structured results + audit trail to Salesforce/Dynamics (in progress).",
    statusLive: "Live",
    statusPlanned: "In Progress",
    tabCompliance: "Compliance Ops",
    monitoring: "Ongoing Monitoring",
    scanNow: "Run Scan",
    alerts: "Monitoring Alerts",
    noAlerts: "No alerts.",
    sarTitle: "Suspicious Activity Report (SAR)",
    createSar: "Create SAR",
    sarName: "Entity",
    sarReason: "Reason",
    sarStatus: "Status",
    sarSubmitted: "Submitted",
    miTitle: "Regulatory MI",
    miTotal: "Total decisions",
    miHigh: "High-risk",
    miByVertical: "By vertical",
    miByAction: "By action",
    miAlerts: "Open alerts",
    miSarTotal: "SARs",
    generatedAt: "Generated",
  },
  "zh-CN": {
    appTitle: "Ceron 控制台",
    gateway: "网关",
    submitTitle: "文档提交",
    vertical: "垂直场景",
    "v.insurance_hk": "港股保险 / 承保理赔",
    "v.family_office": "家族办公室 KYC",
    "v.banking_mortgage": "银行按揭承保",
    "v.securities_suitability": "证券合适性",
    "v.mpf": "强积金 MPF",
    "v.fund_ofc_lpf": "基金 / OFC / LPF",
    docText: "文档文本",
    loadSample: "载入示例",
    asyncMode: "异步提交（看板轮询）",
    submit: "提交并编排",
    kanban: "作业看板",
    statusFilter: "状态筛选",
    "status.all": "全部",
    "status.queued": "排队中",
    "status.processing": "处理中",
    "status.completed": "已完成",
    "status.failed": "失败",
    refresh: "刷新",
    total: "共 {n} 条",
    prev: "上一页",
    next: "下一页",
    page: "第 {n} 页",
    empty: "暂无作业，提交后在此显示。",
    resultTitle: "处理结果",
    reviewer: "审批人",
    approve: "通过",
    manual_review: "人工复核",
    reject: "驳回",
    approved: "已通过",
    rejected: "已驳回",
    manualApprove: "人工通过",
    manualReject: "人工驳回",
    reviewConclusion: "审批结论：{status} · 审批人：{by}{at}",
    manual: "手动",
    timePrefix: "时间：",
    processing: "处理中（异步作业轮询中）…",
    extracted: "抽取字段",
    enrichment: "富集结果",
    dataSource: "数据源：",
    icris: "ICRIS 核验：",
    sanctions: "制裁命中：",
    risk: "风险：",
    decision: "决策建议",
    reason: "理由：",
    riskLevel: "风险等级：",
    yes: "是",
    no: "否",
    riskHigh: "高",
    riskNormal: "正常",
    navWorkspace: "工作台",
    navCompliance: "合规运营",
    navProducts: "产品能力",
    productsTitle: "Ceron 产品能力",
    productsSubtitle: "面向香港金融业的承保与合规自动化：从多入口收件到可审计决策、持续监控与监管申报。",
    pgUnderwriting: "承保与理赔",
    pgCompliance: "合规运营",
    pgData: "数据与集成",
    pExtractName: "文档智能抽取",
    pExtractDesc: "繁中/英双语 OCR + LLM 结构化抽取，8 条业务线专属字段模板。",
    pDecisionName: "决策引擎",
    pDecisionDesc: "风险评分 + SFC/HKMA/MPFA 合规闸口，输出通过/拒绝/转人工及三语理由。",
    pKanbanName: "作业看板与审批",
    pKanbanDesc: "异步流水线、状态筛选与分页、审批留痕审计。",
    pMonitorName: "持续监控",
    pMonitorDesc: "制裁/OFAC/HMT 名单周期重查、触发式 re-KYC，命中自动告警。",
    pSarName: "SAR 申报",
    pSarDesc: "可疑交易申报（JFIU）草稿→提交状态机与留痕。",
    pMiName: "监管 MI 报表",
    pMiDesc: "决策/告警/SAR 聚合，按业务线与结论穿透。",
    pEnrichName: "数据富集",
    pEnrichDesc: "ICRIS/土地注册/信贷局/OFAC/HMT/CRS 8 源可插拔，失败自动降级人工复核。",
    pIntakeName: "多入口收件",
    pIntakeDesc: "API / WhatsApp Business / 企业微信统一接入与异步编排。",
    pSyncName: "CRM 同步",
    pSyncDesc: "结构化结果 + 审计追踪同步 Salesforce/Dynamics（建设中）。",
    statusLive: "已上线",
    statusPlanned: "建设中",
    tabCompliance: "合规运营",
    monitoring: "持续监控",
    scanNow: "立即重查",
    alerts: "监控告警",
    noAlerts: "暂无告警。",
    sarTitle: "可疑交易申报 (SAR)",
    createSar: "生成 SAR",
    sarName: "实体名称",
    sarReason: "申报理由",
    sarStatus: "状态",
    sarSubmitted: "已提交",
    miTitle: "监管 MI 报表",
    miTotal: "决策总数",
    miHigh: "高风险数",
    miByVertical: "按业务线",
    miByAction: "按结论",
    miAlerts: "未结告警",
    miSarTotal: "SAR 总数",
    generatedAt: "生成时间",
  },
};

const LOCALE_ORDER: Locale[] = ["zh-HK", "en", "zh-CN"];
const LOCALE_LABEL: Record<Locale, string> = {
  "zh-HK": "繁體中文",
  en: "English",
  "zh-CN": "简体中文",
};

interface I18nCtx {
  locale: Locale;
  setLocale: (l: Locale) => void;
  t: (key: string) => string;
}

const Ctx = createContext<I18nCtx | null>(null);

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>("zh-HK");

  useEffect(() => {
    try {
      const saved = localStorage.getItem("ceron.locale") as Locale | null;
      if (saved && dict[saved]) setLocaleState(saved);
    } catch {
      /* ignore */
    }
  }, []);

  const setLocale = (l: Locale) => {
    setLocaleState(l);
    try {
      localStorage.setItem("ceron.locale", l);
    } catch {
      /* ignore */
    }
  };

  const t = (key: string) => dict[locale][key] ?? dict["zh-HK"][key] ?? key;

  return <Ctx.Provider value={{ locale, setLocale, t }}>{children}</Ctx.Provider>;
}

export function useT(): I18nCtx {
  const c = useContext(Ctx);
  if (!c) throw new Error("useT must be used within I18nProvider");
  return c;
}

export function LanguageSwitcher() {
  const { locale, setLocale } = useT();
  return (
    <FormControl size="small" sx={{ minWidth: 130 }}>
      <InputLabel>Language</InputLabel>
      <Select
        label="Language"
        value={locale}
        onChange={(e) => setLocale(e.target.value as Locale)}
      >
        {LOCALE_ORDER.map((l) => (
          <MenuItem key={l} value={l}>
            {LOCALE_LABEL[l]}
          </MenuItem>
        ))}
      </Select>
    </FormControl>
  );
}
