"use client";

import { Box, Button, Chip, Grid, Paper, Stack, Typography } from "@mui/material";
import DescriptionIcon from "@mui/icons-material/Description";
import FactCheckIcon from "@mui/icons-material/FactCheck";
import NotificationsActiveIcon from "@mui/icons-material/NotificationsActive";
import GavelIcon from "@mui/icons-material/Gavel";
import SummarizeIcon from "@mui/icons-material/Summarize";
import HubIcon from "@mui/icons-material/Hub";
import Link from "next/link";
import { I18nProvider } from "./i18n";
import MarketingNav from "../components/MarketingNav";
import SiteFooter from "../components/SiteFooter";

function Hero() {
  return (
    <Box sx={{ borderBottom: 1, borderColor: "divider" }}>
      <Box sx={{ maxWidth: 1180, mx: "auto", px: { xs: 2.5, md: 4 }, py: { xs: 8, md: 12 } }}>
        <Chip
          label="FROM APPLICATION TO AUDITABLE DECISION"
          size="small"
          sx={{ mb: 3, bgcolor: "#eef2ff", color: "#1f4dff", fontWeight: 700, letterSpacing: 1 }}
        />
        <Typography variant="h1" sx={{ mb: 3, maxWidth: 900 }}>
          Underwriting automation for Hong Kong finance
        </Typography>
        <Typography variant="h6" color="text.secondary" sx={{ maxWidth: 700, fontWeight: 400, mb: 5 }}>
          Ceron reads every submission — email, portal, WhatsApp or WeCom — enriches it against ICRIS,
          Land Registry, credit bureau and sanctions lists, then returns a decision-ready file with
          SFC / HKMA / MPFA compliance evidence attached.
        </Typography>
        <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
          <Button component={Link} href="/register" size="large" variant="contained">
            Start free
          </Button>
          <Button component={Link} href="/login" size="large" variant="outlined">
            Sign in to console
          </Button>
        </Stack>
        <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 3 }}>
          No credit card · Mock data sources included · Data residency in Hong Kong (PDPO)
        </Typography>
      </Box>
    </Box>
  );
}

function TrustRow() {
  return (
    <Box sx={{ borderBottom: 1, borderColor: "divider", bgcolor: "#fafbfd" }}>
      <Box sx={{ maxWidth: 1180, mx: "auto", px: { xs: 2.5, md: 4 }, py: 5 }}>
        <Typography variant="caption" sx={{ letterSpacing: 1.2, fontWeight: 700, color: "text.secondary" }}>
          BUILT FOR HONG KONG FINANCIAL INSTITUTIONS
        </Typography>
        <Stack direction="row" spacing={5} sx={{ mt: 3, flexWrap: "wrap", rowGap: 3 }}>
          {["Insurance & brokers", "Trusts", "Family offices", "Banks & MPF", "SFC-licensed asset managers"].map(
            (n) => (
              <Typography key={n} variant="subtitle1" fontWeight={700} color="text.secondary">
                {n}
              </Typography>
            )
          )}
        </Stack>
      </Box>
    </Box>
  );
}

function Stats() {
  const items = [
    { k: "8", v: "verticals with dedicated extraction schemas" },
    { k: "6", v: "external data sources behind one pluggable layer" },
    { k: "3", v: "languages across UI, extraction & decision rationale" },
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

const STEPS = [
  {
    k: "INTAKE",
    t: "Emails come in as usual",
    d: "Forward to a mailbox, POST to our API, or let brokers use WhatsApp / WeCom. No behaviour change for your team.",
  },
  {
    k: "EXTRACT",
    t: "Bilingual documents get structured",
    d: "Traditional Chinese, English and simplified input parsed into vertical-specific fields with OCR + LLM.",
  },
  {
    k: "ENRICH",
    t: "Evidence is pulled from real sources",
    d: "ICRIS company search, Land Registry, credit bureau, OFAC / HMT sanctions, CRS / FATCA — fails safe to manual review.",
  },
  {
    k: "DECIDE",
    t: "A decision with reasons, not a score",
    d: "Approve / reject / escalate with a written rationale and every compliance gate recorded for the audit trail.",
  },
];

function HowItWorks() {
  return (
    <Box sx={{ bgcolor: "#fafbfd", borderTop: 1, borderBottom: 1, borderColor: "divider" }}>
      <Box sx={{ maxWidth: 1180, mx: "auto", px: { xs: 2.5, md: 4 }, py: { xs: 7, md: 10 } }}>
        <Typography variant="caption" sx={{ letterSpacing: 1.2, fontWeight: 700, color: "text.secondary" }}>
          HOW IT WORKS
        </Typography>
        <Typography variant="h2" sx={{ mt: 1, mb: 6, maxWidth: 720 }}>
          Four steps from raw submission to defensible decision
        </Typography>
        <Grid container spacing={3}>
          {STEPS.map((s, i) => (
            <Grid item xs={12} md={6} key={s.k}>
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
                    {s.k}
                  </Typography>
                </Stack>
                <Typography variant="h4" sx={{ mb: 1 }}>
                  {s.t}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {s.d}
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
  {
    icon: <DescriptionIcon sx={{ color: "#1f4dff" }} />,
    t: "Document intelligence that handles Chinese",
    d: "Handles HK-specific artefacts — policy schedules, NAR1, trust deeds, MPF records — without template maintenance.",
  },
  {
    icon: <FactCheckIcon sx={{ color: "#1f4dff" }} />,
    t: "Compliance gates inside the pipeline",
    d: "SFC suitability, HKMA LTV / DSR, MPF contribution and OFC / LPF retail checks run before a decision is issued.",
  },
  {
    icon: <HubIcon sx={{ color: "#1f4dff" }} />,
    t: "One integration surface for data sources",
    d: "Swap a provider without touching your workflows. Every source degrades to manual review instead of breaking the run.",
  },
  {
    icon: <NotificationsActiveIcon sx={{ color: "#1f4dff" }} />,
    t: "Ongoing monitoring, not one-off checks",
    d: "Periodic sanctions re-screening and triggered re-KYC keep existing clients under continuous review.",
  },
  {
    icon: <GavelIcon sx={{ color: "#1f4dff" }} />,
    t: "SAR filing and regulatory MI",
    d: "Draft-to-submitted suspicious activity reports plus MI dashboards your compliance team can hand to regulators.",
  },
  {
    icon: <SummarizeIcon sx={{ color: "#1f4dff" }} />,
    t: "Every decision explained",
    d: "Field-level evidence, weighted reasons and trilingual rationale — built for model governance.",
  },
];

function Features() {
  return (
    <Box sx={{ maxWidth: 1180, mx: "auto", px: { xs: 2.5, md: 4 }, py: { xs: 7, md: 10 } }}>
      <Typography variant="caption" sx={{ letterSpacing: 1.2, fontWeight: 700, color: "text.secondary" }}>
        CAPABILITIES
      </Typography>
      <Typography variant="h2" sx={{ mt: 1, mb: 6, maxWidth: 760 }}>
        Everything a Hong Kong underwriting desk needs, out of the box
      </Typography>
      <Grid container spacing={3}>
        {FEATURES.map((f) => (
          <Grid item xs={12} md={4} key={f.t}>
            <Box>
              {f.icon}
              <Typography variant="h6" sx={{ mt: 1.5, mb: 0.5 }}>
                {f.t}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {f.d}
              </Typography>
            </Box>
          </Grid>
        ))}
      </Grid>
    </Box>
  );
}

function QuoteSection() {
  return (
    <Box sx={{ bgcolor: "#0b1a3a", color: "#fff" }}>
      <Box sx={{ maxWidth: 1180, mx: "auto", px: { xs: 2.5, md: 4 }, py: { xs: 7, md: 10 } }}>
        <Typography variant="h3" sx={{ maxWidth: 880, mb: 3, lineHeight: 1.4 }}>
          “We want evidence on every decision. Ceron sits at the top of our funnel because it handles
          the most important data first.”
        </Typography>
        <Typography variant="body2" sx={{ opacity: 0.8 }}>
          Head of Operations · Hong Kong family office
        </Typography>
      </Box>
    </Box>
  );
}

function FinalCta() {
  return (
    <Box sx={{ borderTop: 1, borderColor: "divider" }}>
      <Box sx={{ maxWidth: 1180, mx: "auto", px: { xs: 2.5, md: 4 }, py: { xs: 7, md: 10 }, textAlign: "center" }}>
        <Typography variant="caption" sx={{ letterSpacing: 1.2, fontWeight: 700, color: "text.secondary" }}>
          GET STARTED IN MINUTES
        </Typography>
        <Typography variant="h2" sx={{ mt: 1, mb: 4 }}>
          See a submission become a decision
        </Typography>
        <Stack direction={{ xs: "column", sm: "row" }} spacing={2} justifyContent="center">
          <Button component={Link} href="/register" size="large" variant="contained">
            Create free account
          </Button>
          <Button component={Link} href="/products" size="large" variant="outlined">
            Tour the platform
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
