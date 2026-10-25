"use client";

import Link from "next/link";
import { Box, Divider, Grid, Stack, Typography } from "@mui/material";
import HubIcon from "@mui/icons-material/Hub";
import { useT } from "../app/i18n";

export default function SiteFooter() {
  const { t } = useT();

  const columns = [
    {
      titleKey: "footerPlatform",
      items: [
        { key: "fProductCaps", href: "/products" },
        { key: "fCompare", href: "/compare" },
        { key: "fArchitecture", href: "/products#architecture" },
        { key: "fConsole", href: "/app" },
      ],
    },
    {
      titleKey: "footerCompliance",
      items: [
        { key: "fMonitoring", href: "/app/compliance" },
        { key: "fSar", href: "/app/compliance" },
        { key: "fMi", href: "/app/compliance" },
      ],
    },
    {
      titleKey: "footerCompany",
      items: [
        { key: "fGithub", href: "https://github.com/wjc1wjc2wjc3/Ceron" },
        { key: "fContact", href: "mailto:hello@ceron.ai" },
      ],
    },
  ];

  return (
    <Box sx={{ borderTop: 1, borderColor: "divider", bgcolor: "#fafbfd" }}>
      <Box sx={{ maxWidth: 1180, mx: "auto", px: { xs: 2.5, md: 4 }, py: 7 }}>
        <Grid container spacing={4}>
          <Grid item xs={12} md={4}>
            <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1.5 }}>
              <HubIcon sx={{ color: "primary.main" }} />
              <Typography variant="h6" fontWeight={800}>
                Ceron
              </Typography>
            </Stack>
            <Typography variant="body2" color="text.secondary" sx={{ maxWidth: 320 }}>
              {t("footerBlurb")}
            </Typography>
          </Grid>
          {columns.map((c) => (
            <Grid item xs={6} md={2.66} key={c.titleKey}>
              <Typography variant="caption" fontWeight={700} color="text.secondary">
                {t(c.titleKey)}
              </Typography>
              <Stack spacing={1} sx={{ mt: 2 }}>
                {c.items.map((i) => (
                  <Typography
                    key={i.key}
                    variant="body2"
                    component={Link}
                    href={i.href}
                    sx={{ textDecoration: "none", color: "text.primary", "&:hover": { color: "primary.main" } }}
                  >
                    {t(i.key)}
                  </Typography>
                ))}
              </Stack>
            </Grid>
          ))}
        </Grid>
        <Divider sx={{ my: 4 }} />
        <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" spacing={1}>
          <Typography variant="caption" color="text.secondary">
            {t("footerRights").replace("{year}", String(new Date().getFullYear()))}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {t("footerGates")}
          </Typography>
        </Stack>
      </Box>
    </Box>
  );
}
