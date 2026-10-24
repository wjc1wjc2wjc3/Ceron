"use client";

import Link from "next/link";
import {
  Box, Button, Card, CardActionArea, CardContent, Chip, Grid, Stack, Typography,
} from "@mui/material";
import DescriptionIcon from "@mui/icons-material/Description";
import FactCheckIcon from "@mui/icons-material/FactCheck";
import ViewKanbanIcon from "@mui/icons-material/ViewKanban";
import NotificationsActiveIcon from "@mui/icons-material/NotificationsActive";
import GavelIcon from "@mui/icons-material/Gavel";
import SummarizeIcon from "@mui/icons-material/Summarize";
import HubIcon from "@mui/icons-material/Hub";
import MarkEmailReadIcon from "@mui/icons-material/MarkEmailRead";
import SyncIcon from "@mui/icons-material/Sync";
import MarketingNav from "../../components/MarketingNav";
import SiteFooter from "../../components/SiteFooter";
import { I18nProvider, useT } from "../i18n";

type Status = "live" | "planned";

interface ProductItem {
  icon: React.ReactNode;
  key: string; // i18n 前缀
  href?: string;
  status: Status;
}

interface ProductGroup {
  titleKey: string;
  items: ProductItem[];
}

const GROUPS: ProductGroup[] = [
  {
    titleKey: "pgUnderwriting",
    items: [
      { icon: <DescriptionIcon color="primary" />, key: "pExtract", href: "/app", status: "live" },
      { icon: <FactCheckIcon color="primary" />, key: "pDecision", href: "/app", status: "live" },
      { icon: <ViewKanbanIcon color="primary" />, key: "pKanban", href: "/app", status: "live" },
    ],
  },
  {
    titleKey: "pgCompliance",
    items: [
      { icon: <NotificationsActiveIcon color="primary" />, key: "pMonitor", href: "/app/compliance", status: "live" },
      { icon: <GavelIcon color="primary" />, key: "pSar", href: "/app/compliance", status: "live" },
      { icon: <SummarizeIcon color="primary" />, key: "pMi", href: "/app/compliance", status: "live" },
    ],
  },
  {
    titleKey: "pgData",
    items: [
      { icon: <HubIcon color="primary" />, key: "pEnrich", href: "/", status: "live" },
      { icon: <MarkEmailReadIcon color="primary" />, key: "pIntake", status: "live" },
      { icon: <SyncIcon color="primary" />, key: "pSync", status: "planned" },
    ],
  },
];

const WHY = [
  { nameKey: "why1Name", descKey: "why1Desc", color: "#1565c0" },
  { nameKey: "why2Name", descKey: "why2Desc", color: "#2e7d32" },
  { nameKey: "why3Name", descKey: "why3Desc", color: "#7b1fa2" },
];

/** 装饰性控制台预览（SVG 截图风格），用于产品落地页。 */
function PreviewSVG({ variant, title }: { variant: "workbench" | "compliance"; title: string }) {
  const win = (
    <g>
      <rect x="0" y="0" width="480" height="300" rx="12" fill="#ffffff" stroke="#cfd8e3" />
      <rect x="0" y="0" width="480" height="34" rx="12" fill="#1565c0" />
      <rect x="0" y="22" width="480" height="12" fill="#1565c0" />
      <circle cx="18" cy="17" r="5" fill="#ff5f56" />
      <circle cx="36" cy="17" r="5" fill="#ffbd2e" />
      <circle cx="54" cy="17" r="5" fill="#27c93f" />
      <text x="240" y="21" textAnchor="middle" fontSize="12" fill="#ffffff" fontWeight={600}>{title}</text>
      <rect x="0" y="34" width="74" height="266" fill="#eef4fb" />
      <rect x="14" y="54" width="46" height="8" rx="4" fill="#bbdefb" />
      <rect x="14" y="74" width="46" height="8" rx="4" fill="#bbdefb" />
      <rect x="14" y="94" width="46" height="8" rx="4" fill="#bbdefb" />
    </g>
  );
  if (variant === "workbench") {
    return (
      <svg viewBox="0 0 480 300" width="100%" role="img" aria-label={title}>
        {win}
        <text x="92" y="62" fontSize="14" fontWeight={700} fill="#0d47a1">承保工作台</text>
        {[110, 158, 206].map((y, i) => (
          <g key={i}>
            <rect x="92" y={y} width="372" height="40" rx="8" fill="#f7fafd" stroke="#e3e9f0" />
            <rect x="104" y={y + 13} width="120" height="14" rx="4" fill="#e3f2fd" />
            <rect x="236" y={y + 13} width="90" height="14" rx="4" fill="#eceff1" />
            <rect x="338" y={y + 10} width="56" height="20" rx="10" fill={i === 1 ? "#fff3e0" : "#e8f5e9"} />
            <rect x="346" y={y + 16} width="40" height="8" rx="4" fill={i === 1 ? "#ef6c00" : "#2e7d32"} />
          </g>
        ))}
      </svg>
    );
  }
  return (
    <svg viewBox="0 0 480 300" width="100%" role="img" aria-label={title}>
      {win}
      <text x="92" y="62" fontSize="14" fontWeight={700} fill="#0d47a1">合規運營</text>
      {[
        { y: 104, c: "#ffcdd2", t: "#c62828" },
        { y: 156, c: "#fff3e0", t: "#ef6c00" },
        { y: 208, c: "#e8f5e9", t: "#2e7d32" },
      ].map((row, i) => (
        <g key={i}>
          <rect x="92" y={row.y} width="372" height="44" rx="8" fill="#f7fafd" stroke="#e3e9f0" />
          <rect x="92" y={row.y} width="6" height="44" rx="3" fill={row.t} />
          <rect x="110" y={row.y + 12} width="200" height="12" rx="4" fill={row.c} />
          <rect x="110" y={row.y + 28} width="120" height="8" rx="4" fill="#eceff1" />
        </g>
      ))}
    </svg>
  );
}

function Products() {
  const { t } = useT();
  return (
    <Box sx={{ maxWidth: 1200, mx: "auto", p: { xs: 2, md: 4 } }}>
      {/* Hero */}
      <Box sx={{ textAlign: "center", py: 5 }}>
        <Typography variant="h3" fontWeight={800} color="primary.main">
          {t("productsTitle")}
        </Typography>
        <Typography variant="h6" color="text.secondary" sx={{ mt: 2, fontWeight: 400 }}>
          {t("productsSubtitle")}
        </Typography>
        <Button variant="contained" size="large" component={Link} href="/" sx={{ mt: 3 }}>
          {t("ctaExplore")}
        </Button>
      </Box>

      {/* 架构图 */}
      <Box sx={{ mb: 7 }}>
        <Typography variant="h5" fontWeight={700} sx={{ mb: 1 }}>
          {t("architectureTitle")}
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          {t("architectureDesc")}
        </Typography>
        <Box
          component="img"
          src="/architecture.svg"
          alt="Ceron 平台架构"
          sx={{ width: "100%", border: "1px solid", borderColor: "divider", borderRadius: 2, bgcolor: "#f7fafd" }}
        />
      </Box>

      {/* 产品能力 */}
      {GROUPS.map((g) => (
        <Box key={g.titleKey} sx={{ mb: 5 }}>
          <Typography variant="h6" fontWeight={700} sx={{ mb: 2 }}>
            {t(g.titleKey)}
          </Typography>
          <Grid container spacing={2}>
            {g.items.map((item) => (
              <Grid item xs={12} sm={6} md={4} key={item.key}>
                <Card variant="outlined" sx={{ height: "100%" }}>
                  <CardActionArea
                    component={item.href ? Link : "div"}
                    href={item.href}
                    disabled={!item.href}
                    sx={{ height: "100%" }}
                  >
                    <CardContent>
                      <Stack direction="row" spacing={1.5} alignItems="flex-start">
                        {item.icon}
                        <Box sx={{ flexGrow: 1 }}>
                          <Stack direction="row" justifyContent="space-between" alignItems="center">
                            <Typography variant="subtitle1" fontWeight={600}>
                              {t(`${item.key}Name`)}
                            </Typography>
                            <Chip
                              size="small"
                              label={t(item.status === "live" ? "statusLive" : "statusPlanned")}
                              color={item.status === "live" ? "success" : "default"}
                            />
                          </Stack>
                          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                            {t(`${item.key}Desc`)}
                          </Typography>
                        </Box>
                      </Stack>
                    </CardContent>
                  </CardActionArea>
                </Card>
              </Grid>
            ))}
          </Grid>
        </Box>
      ))}

      {/* 控制台预览 */}
      <Box sx={{ mb: 7 }}>
        <Typography variant="h5" fontWeight={700} sx={{ mb: 2 }}>
          {t("previewTitle")}
        </Typography>
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Card variant="outlined"><CardContent><PreviewSVG variant="workbench" title={t("previewWorkbench")} /></CardContent></Card>
          </Grid>
          <Grid item xs={12} md={6}>
            <Card variant="outlined"><CardContent><PreviewSVG variant="compliance" title={t("previewCompliance")} /></CardContent></Card>
          </Grid>
        </Grid>
      </Box>

      {/* 为什么选择 Ceron */}
      <Box sx={{ mb: 6 }}>
        <Typography variant="h5" fontWeight={700} sx={{ mb: 2 }}>
          {t("whyTitle")}
        </Typography>
        <Grid container spacing={2}>
          {WHY.map((w) => (
            <Grid item xs={12} md={4} key={w.nameKey}>
              <Card variant="outlined" sx={{ height: "100%", borderTop: `3px solid ${w.color}` }}>
                <CardContent>
                  <Typography variant="subtitle1" fontWeight={700} sx={{ color: w.color }}>
                    {t(w.nameKey)}
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                    {t(w.descKey)}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      </Box>
    </Box>
  );
}

export default function ProductsPage() {
  return (
    <I18nProvider>
      <MarketingNav />
      <Products />
      <SiteFooter />
    </I18nProvider>
  );
}
