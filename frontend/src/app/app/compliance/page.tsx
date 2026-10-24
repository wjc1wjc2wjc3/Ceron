"use client";

import NavBar from "../../../components/NavBar";
import ComplianceView from "../../../components/ComplianceView";
import { I18nProvider } from "../../i18n";

export default function ConsoleCompliancePage() {
  return (
    <I18nProvider>
      <NavBar />
      <ComplianceView />
    </I18nProvider>
  );
}
