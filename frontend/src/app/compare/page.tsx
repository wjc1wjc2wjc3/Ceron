"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  Alert, Box, Button, Chip, Grid, Paper, Stack, Table, TableBody, TableCell,
  TableContainer, TableHead, TableRow, Typography,
} from "@mui/material";
import CheckIcon from "@mui/icons-material/Check";
import RemoveIcon from "@mui/icons-material/Remove";
import CloseIcon from "@mui/icons-material/Close";
import MarketingNav from "../../components/MarketingNav";
import SiteFooter from "../../components/SiteFooter";
import { I18nProvider, useT } from "../i18n";

type Mark = "full" | "partial" | "none";

// 对照矩阵：四类常见方案 vs Ceron（只做类别对照，不点名厂商）
const ROWS: { key: string; ceron: Mark; generic: Mark; idp: Mark; aml: Mark; core: Mark }[] = [
  { key: "rowEvidence", ceron: "full", generic: "none", idp: "partial", aml: "full", core: "partial" },
  { key: "rowGates", ceron: "full", generic: "none", idp: "none", aml: "partial", core: "partial" },
  { key: "rowLocalSrc", ceron: "full", generic: "none", idp: "none", aml: "partial", core: "none" },
  { key: "rowTrilingual", ceron: "full", generic: "partial", idp: "none", aml: "none", core: "partial" },
  { key: "rowFailSafe", ceron: "full", generic: "none", idp: "none", aml: "partial", core: "none" },
  { key: "rowAudit", ceron: "full", generic: "none", idp: "partial", aml: "partial", core: "none" },
  { key: "rowResidency", ceron: "full", generic: "partial", idp: "partial", aml: "none", core: "partial" },
  { key: "rowModelChoice", ceron: "full", generic: "partial", idp: "none", aml: "none", core: "none" },
  { key: "rowSelfHost", ceron: "full", generic: "partial", idp: "partial", aml: "none", core: "none" },
  { key: "rowUbo", ceron: "full", generic: "none", idp: "none", aml: "partial", core: "none" },
];

function MarkCell({ mark }: { mark: Mark }) {
  const { t } = useT();
  const cfg = {
    full: { icon: <CheckIcon fontSize="small" />, color: "success" as const, label: t("markFull") },
    partial: { icon: <RemoveIcon fontSize="small" />, color: "warning" as const, label: t("markPartial") },
    none: { icon: <CloseIcon fontSize="small" />, color: "default" as const, label: t("markNone") },
  }[mark];
  return (
    <Chip size="small" icon={cfg.icon} label={cfg.label} color={cfg.color} variant={mark === "none" ? "outlined" : "filled"} />
  );
}

function CompareView() {
  const { t } = useT();
  const [cap, setCap] = useState<any>(null);
  const [bench] = useState({ accuracy: 1, total: 63, mode: "rule-fallback" });

  useEffect(() => {
    fetch("/py/v1/capabilities")
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => setCap(d))
      .catch(() => setCap(null));
  }, []);

  return (
    <Box>
      <MarketingNav />
      <Box sx={{ borderBottom: 1, borderColor: "divider" }}>
        <Box sx={{ maxWidth: 1180, mx: "auto", px: { xs: 2.5, md: 4 }, py: { xs: 6, md: 9 } }}>
          <Typography variant="caption" sx={{ letterSpacing: 1.2, fontWeight: 700, color: "text.secondary" }}>
            {t("compareKicker")}
          </Typography>
          <Typography variant="h2" sx={{ mt: 1, mb: 2, maxWidth: 820 }}>
            {t("compareTitle")}
          </Typography>
          <Typography variant="body1" color="text.secondary" sx={{ maxWidth: 780 }}>
            {t("compareSub")}
          </Typography>
        </Box>
      </Box>

      {/* 覆盖度：数字由后端实时统计，避免各处手写不一致 */}
      <Box sx={{ maxWidth: 1180, mx: "auto", px: { xs: 2.5, md: 4 }, py: { xs: 5, md: 7 } }}>
        <Typography variant="h6" fontWeight={700} sx={{ mb: 2 }}>
          {t("capTitle")}
        </Typography>
        <Grid container spacing={2}>
          {[
            { k: "capVerticals", v: cap?.verticals?.count },
            { k: "capSources", v: cap ? `${cap.data_sources.configured}/${cap.data_sources.implemented}` : undefined },
            { k: "capRules", v: cap?.compliance_gates?.rules },
            { k: "capModels", v: cap?.models?.presets },
            { k: "capVersion", v: cap?.compliance_gates?.version },
            { k: "capCheckpoints", v: cap?.review_checkpoints },
          ].map((x) => (
            <Grid item xs={6} md={2} key={x.k}>
              <Paper variant="outlined" sx={{ p: 2, textAlign: "center" }}>
                <Typography variant="h4" fontWeight={800} color="primary.main">
                  {x.v ?? "—"}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {t(x.k)}
                </Typography>
              </Paper>
            </Grid>
          ))}
        </Grid>
      </Box>

      {/* 对照矩阵 */}
      <Box sx={{ maxWidth: 1180, mx: "auto", px: { xs: 2.5, md: 4 }, pb: { xs: 5, md: 7 } }}>
        <TableContainer component={Paper} variant="outlined">
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell sx={{ fontWeight: 700 }}>{t("colCriterion")}</TableCell>
                <TableCell align="center" sx={{ fontWeight: 700, bgcolor: "#eef2ff" }}>{t("colCeron")}</TableCell>
                <TableCell align="center" sx={{ fontWeight: 700 }}>{t("colGeneric")}</TableCell>
                <TableCell align="center" sx={{ fontWeight: 700 }}>{t("colIdp")}</TableCell>
                <TableCell align="center" sx={{ fontWeight: 700 }}>{t("colAml")}</TableCell>
                <TableCell align="center" sx={{ fontWeight: 700 }}>{t("colCoreSys")}</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {ROWS.map((r) => (
                <TableRow key={r.key} hover>
                  <TableCell>{t(r.key)}</TableCell>
                  <TableCell align="center" sx={{ bgcolor: "#f7f9ff" }}><MarkCell mark={r.ceron} /></TableCell>
                  <TableCell align="center"><MarkCell mark={r.generic} /></TableCell>
                  <TableCell align="center"><MarkCell mark={r.idp} /></TableCell>
                  <TableCell align="center"><MarkCell mark={r.aml} /></TableCell>
                  <TableCell align="center"><MarkCell mark={r.core} /></TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Box>

      {/* 评测基准 */}
      <Box sx={{ bgcolor: "#fafbfd", borderTop: 1, borderBottom: 1, borderColor: "divider" }}>
        <Box sx={{ maxWidth: 1180, mx: "auto", px: { xs: 2.5, md: 4 }, py: { xs: 5, md: 7 } }}>
          <Typography variant="h6" fontWeight={700} sx={{ mb: 1 }}>
            {t("benchTitle")}
          </Typography>
          <Stack direction="row" spacing={2} alignItems="baseline" sx={{ mb: 1 }}>
            <Typography variant="h3" color="primary.main" fontWeight={800}>
              {Math.round(bench.accuracy * 100)}%
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {bench.total} {t("benchFields")} · {bench.mode === "rule-fallback" ? t("benchModeRule") : t("benchModeLlm")}
            </Typography>
          </Stack>
          <Typography variant="body2" color="text.secondary" sx={{ maxWidth: 760 }}>
            {t("benchNote")}
          </Typography>
        </Box>
      </Box>

      {/* CTA */}
      <Box sx={{ maxWidth: 1180, mx: "auto", px: { xs: 2.5, md: 4 }, py: { xs: 6, md: 8 }, textAlign: "center" }}>
        {!cap && (
          <Alert severity="info" sx={{ mb: 3, textAlign: "left" }}>
            /py/v1/capabilities 暫不可用（後端未啟動）— 覆蓋度數字將在服務可用時自動填充。
          </Alert>
        )}
        <Typography variant="h3" sx={{ mb: 3 }}>
          {t("ctaTitle")}
        </Typography>
        <Stack direction={{ xs: "column", sm: "row" }} spacing={2} justifyContent="center">
          <Button component={Link} href="/register" size="large" variant="contained">
            {t("ctaBtn1")}
          </Button>
          <Button component={Link} href="/products" size="large" variant="outlined">
            {t("ctaBtn2")}
          </Button>
        </Stack>
      </Box>
      <SiteFooter />
    </Box>
  );
}

export default function ComparePage() {
  return (
    <I18nProvider>
      <CompareView />
    </I18nProvider>
  );
}
