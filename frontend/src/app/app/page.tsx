"use client";

import NavBar from "../../components/NavBar";
import { I18nProvider } from "../i18n";
// JobsView 定义在 `app/page.tsx`（承保工作台），控制台与营销页共用同一实现。
import { JobsView } from "../page";

export default function ConsolePage() {
  return (
    <I18nProvider>
      <NavBar />
      <JobsView />
    </I18nProvider>
  );
}
