"use client";

import { Box, Button, Chip, Grid, Paper, Stack, Typography } from "@mui/material";
import DescriptionIcon from "@mui/icons-material/Description";
import FactCheckIcon from "@mui/icons-material/FactCheck";
import NotificationsActiveIcon from "@mui/icons-material/NotificationsActive";
import GavelIcon from "@mui/icons-material/Gavel";
import SummarizeIcon from "@mui/icons-material/Summarize";
import HubIcon from "@mui/icons-material/Hub";
import Link from "next/link";
import { I18nProvider, useT } from "./i18n";
import MarketingNav from "../components/MarketingNav";
import SiteFooter from "../components/SiteFooter";

function Hero() {
  const { t } = useT();
  return (
    <Box sx={{ borderBottom: 1, borderColor: "divider" }}>
      <Box sx={{ maxWidth: 1180, mx: "auto", px: { xs: 2.5, md: 4 }, py: { xs: 8, md: 12 } }}>
        <Chip
          label={t("heroBadge")}
          size="small"
          sx={{ mb: 3, bgcolor: "#eef2ff", color: "#1f4dff", fontWeight: 700, letterSpacing: 1 }}
        />
        <Typography variant="h1" sx={{ mb: 3, maxWidth: 900 }}>
          {t("heroTitle")}
        </Typography>
        <Typography variant="h6" color="text.secondary" sx={{ maxWidth: 700, fontWeight: 400, mb: 5 }}>
          {t("heroSub")}
        </Typography>
        <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
          <Button component={Link} href="/register" size="large" variant="contained">
            {t("heroCta1")}
          </Button>
          <Button component={Link} href="/login" size="large" variant="outlined">
            {t("heroCta2")}
          </Button>
        </Stack>
        <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 3 }}>
          {t("heroNote")}
        </Typography>
      </Box>
    </Box>
  );
}

function TrustRow() {
  const { t } = useT();
  const keys = ["trust1", "trust2", "trust3", "trust4", "trust5"];
  return (
    <Box sx={{ borderBottom: 1, borderColor: "divider", bgcolor: "#fafbfd" }}>
      <Box sx={{ maxWidth: 1180, mx: "auto", px: { xs: 2.5, md: 4 }, py: 5 }}>
        <Typography variant="caption" sx={{ letterSpacing: 1.2, fontWeight: 700, color: "text.secondary" }}>
          {t("trustLabel")}
        </Typography>
        <Stack direction="row" spacing={5} sx={{ mt: 3, flexWrap: "wrap", rowGap: 3 }}>
          {keys.map((k) => (
            <Typography key={k} variant="subtitle1" fontWeight={700} color="text.secondary">
              {t(k)}
            </Typography>
          ))}
        </Stack>
      </Box>
    </Box>
  );
}

function Stats() {
  const { t } = useT();
  const items = [
    { k: "8", v: t("stat1v") },
    { k: "6", v: t("stat2v") },
    { k: "3", v: t("stat3v") },
  ];
  return (
    <Box sx={{ maxWidth: 1180, mx: "auto", px: { xs: 2.5, md: 4 }, py: { xs: 6, md: 9 } }}>
      <Grid container spacing={4}>
        {items.map((s) => (
          <Grid item xs={12} md={4} key={s.k}>
            <Typography variant="h2" color="primary.main" fontWeight={800}>
              {s.k}
            </Typography>
            <Typography variant="body1" color="text.secondary" sx={{ mt: 1 }}>
              {s.v}
            </Typography>
          </Grid>
        ))}
      </Grid>
    </Box>
  );
}

function HowItWorks() {
  const { t } = useT();
  const steps = [1, 2, 3, 4];
  return (
    <Box sx={{ bgcolor: "#fafbfd", borderTop: 1, borderBottom: 1, borderColor: "divider" }}>
      <Box sx={{ maxWidth: 1180, mx: "auto", px: { xs: 2.5, md: 4 }, py: { xs: 7, md: 10 } }}>
        <Typography variant="caption" sx={{ letterSpacing: 1.2, fontWeight: 700, color: "text.secondary" }}>
          {t("howLabel")}
        </Typography>
        <Typography variant="h2" sx={{ mt: 1, mb: 6, maxWidth: 720 }}>
          {t("howTitle")}
        </Typography>
        <Grid container spacing={3}>
          {steps.map((n, i) => (
            <Grid item xs={12} md={6} key={n}>
              <Paper variant="outlined" sx={{ p: 4, height: "100%" }}>
                <Stack direction="row" spacing={2} alignItems="center" sx={{ mb: 2 }}>
                  <Box
                    sx={{
                      width: 34, height: 34, borderRadius: "50%", bgcolor: "#eef2ff",
                      color: "#1f4dff", display: "grid", placeItems: "center", fontWeight: 800,
                    }}
                  >
                    {i + 1}
                  </Box>
                  <Typography variant="caption" fontWeight={700} color="text.secondary" sx={{ letterSpacing: 1 }}>
                    {t(`step${n}k`)}
                  </Typography>
                </Stack>
                <Typography variant="h4" sx={{ mb: 1 }}>
                  {t(`step${n}t`)}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {t(`step${n}d`)}
                </Typography>
              </Paper>
            </Grid>
          ))}
        </Grid>
      </Box>
    </Box>
  );
}

const FEATURES = [
  { icon: <DescriptionIcon sx={{ color: "#1f4dff" }} />, n: 1 },
  { icon: <FactCheckIcon sx={{ color: "#1f4dff" }} />, n: 2 },
  { icon: <HubIcon sx={{ color: "#1f4dff" }} />, n: 3 },
  { icon: <NotificationsActiveIcon sx={{ color: "#1f4dff" }} />, n: 4 },
  { icon: <GavelIcon sx={{ color: "#1f4dff" }} />, n: 5 },
  { icon: <SummarizeIcon sx={{ color: "#1f4dff" }} />, n: 6 },
];

function Features() {
  const { t } = useT();
  return (
    <Box sx={{ maxWidth: 1180, mx: "auto", px: { xs: 2.5, md: 4 }, py: { xs: 7, md: 10 } }}>
      <Typography variant="caption" sx={{ letterSpacing: 1.2, fontWeight: 700, color: "text.secondary" }}>
        {t("featLabel")}
      </Typography>
      <Typography variant="h2" sx={{ mt: 1, mb: 6, maxWidth: 760 }}>
        {t("featTitle")}
      </Typography>
      <Grid container spacing={3}>
        {FEATURES.map((f) => (
          <Grid item xs={12} md={4} key={f.n}>
            <Box>
              {f.icon}
              <Typography variant="h6" sx={{ mt: 1.5, mb: 0.5 }}>
                {t(`feat${f.n}t`)}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {t(`feat${f.n}d`)}
              </Typography>
            </Box>
          </Grid>
        ))}
      </Grid>
    </Box>
  );
}

function QuoteSection() {
  const { t } = useT();
  return (
    <Box sx={{ bgcolor: "#0b1a3a", color: "#fff" }}>
      <Box sx={{ maxWidth: 1180, mx: "auto", px: { xs: 2.5, md: 4 }, py: { xs: 7, md: 10 } }}>
        <Typography variant="h3" sx={{ maxWidth: 880, mb: 3, lineHeight: 1.4 }}>
          {t("quoteText")}
        </Typography>
        <Typography variant="body2" sx={{ opacity: 0.8 }}>
          {t("quoteBy")}
        </Typography>
      </Box>
    </Box>
  );
}

function FinalCta() {
  const { t } = useT();
  return (
    <Box sx={{ borderTop: 1, borderColor: "divider" }}>
      <Box sx={{ maxWidth: 1180, mx: "auto", px: { xs: 2.5, md: 4 }, py: { xs: 7, md: 10 }, textAlign: "center" }}>
        <Typography variant="caption" sx={{ letterSpacing: 1.2, fontWeight: 700, color: "text.secondary" }}>
          {t("ctaLabel")}
        </Typography>
        <Typography variant="h2" sx={{ mt: 1, mb: 4 }}>
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
    </Box>
  );
}

export default function Home() {
  return (
    <I18nProvider>
      <MarketingNav />
      <Hero />
      <TrustRow />
      <Stats />
      <HowItWorks />
      <Features />
      <QuoteSection />
      <FinalCta />
      <SiteFooter />
    </I18nProvider>
  );
}
