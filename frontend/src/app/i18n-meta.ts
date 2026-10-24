// 服务端可用的元数据字典：不标注 "use client"，供 root layout 的 generateMetadata 直接读取，
// 同时被 i18n.tsx 复用做客户端标题同步。
export type MetaEntry = { title: string; description: string };

export const DEFAULT_LOCALE = "zh-HK";

export const LOCALE_META: Record<string, MetaEntry> = {
  "zh-HK": {
    title: "Ceron — 香港金融業承保與合規自動化",
    description:
      "Ceron 把原始申請轉化為可審計決策：面向香港保險、信託與家族辦公室的雙語抽取、ICRIS / 信貸資料庫富集，以及 SFC / HKMA / MPFA 合規閘口。",
  },
  en: {
    title: "Ceron — Underwriting automation for Hong Kong finance",
    description:
      "Ceron turns raw submissions into auditable decisions for Hong Kong insurance, trusts and family offices: bilingual extraction, ICRIS / credit bureau enrichment, and SFC / HKMA / MPFA compliance gates.",
  },
  "zh-CN": {
    title: "Ceron — 香港金融业承保与合规自动化",
    description:
      "Ceron 把原始申请转化为可审计决策：面向香港保险、信托与家族办公室的双语抽取、ICRIS / 信贷数据库富集，以及 SFC / HKMA / MPFA 合规闸口。",
  },
};

// <html lang>：简体中文使用 zh-Hans，便于浏览器/读屏器正确选字形。
export function htmlLang(locale: string): string {
  return locale === "zh-CN" ? "zh-Hans" : locale;
}

export function metaFor(locale: string | undefined): MetaEntry {
  return (locale && LOCALE_META[locale]) || LOCALE_META[DEFAULT_LOCALE];
}
