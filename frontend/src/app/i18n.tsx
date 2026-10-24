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
  },
  en: {
    appTitle: "Ceron Console",
    gateway: "Gateway",
    submitTitle: "Document Intake",
    vertical: "Vertical",
    "v.insurance_hk": "HK Equity Insurance / Underwriting",
    "v.family_office": "Family Office KYC",
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
  },
  "zh-CN": {
    appTitle: "Ceron 控制台",
    gateway: "网关",
    submitTitle: "文档提交",
    vertical: "垂直场景",
    "v.insurance_hk": "港股保险 / 承保理赔",
    "v.family_office": "家族办公室 KYC",
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
