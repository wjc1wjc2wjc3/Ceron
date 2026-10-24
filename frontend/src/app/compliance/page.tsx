"use client";

import { Box } from "@mui/material";
import NavBar from "../../components/NavBar";
import ComplianceView from "../../components/ComplianceView";
import { I18nProvider } from "../i18n";

export default function CompliancePage() {
  return (
    <I18nProvider>
      <NavBar />
      <Box sx={{ p: 3, maxWidth: 1200, mx: "auto" }}>
        <ComplianceView />
      </Box>
    </I18nProvider>
  );
}
