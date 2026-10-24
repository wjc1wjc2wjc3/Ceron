"use client";

import Link from "next/link";
import {
  Box, Card, CardActionArea, CardContent, Chip, Grid, Stack, Typography,
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
import NavBar from "../../components/NavBar";
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
      { icon: <DescriptionIcon color="primary" />, key: "pExtract", href: "/", status: "live" },
      { icon: <FactCheckIcon color="primary" />, key: "pDecision", href: "/", status: "live" },
      { icon: <ViewKanbanIcon color="primary" />, key: "pKanban", href: "/", status: "live" },
    ],
  },
  {
    titleKey: "pgCompliance",
    items: [
      { icon: <NotificationsActiveIcon color="primary" />, key: "pMonitor", href: "/compliance", status: "live" },
      { icon: <GavelIcon color="primary" />, key: "pSar", href: "/compliance", status: "live" },
      { icon: <SummarizeIcon color="primary" />, key: "pMi", href: "/compliance", status: "live" },
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

function Products() {
  const { t, locale } = useT();
  return (
    <Box sx={{ p: 3, maxWidth: 1200, mx: "auto" }}>
      <Typography variant="h4" sx={{ mb: 1 }}>
        {t("productsTitle")}
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
        {t("productsSubtitle")}
      </Typography>

      {GROUPS.map((g) => (
        <Box key={g.titleKey} sx={{ mb: 4 }}>
          <Typography variant="h6" sx={{ mb: 2 }}>
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

      <Typography variant="caption" color="text.secondary">
        {locale === "en"
          ? "Regulated for Hong Kong: SFC / HKMA / MPFA / IRD gates built into the decision engine."
          : "决策引擎内置香港监管合规閘口：SFC / HKMA / MPFA / 稅務。" }
      </Typography>
    </Box>
  );
}

export default function ProductsPage() {
  return (
    <I18nProvider>
      <NavBar />
      <Products />
    </I18nProvider>
  );
}
