"use client";

import NavBar from "../../components/NavBar";
import { I18nProvider } from "../i18n";
import JobsView from "../../components/JobsView";

export default function ConsolePage() {
  return (
    <I18nProvider>
      <NavBar />
      <JobsView />
    </I18nProvider>
  );
}
