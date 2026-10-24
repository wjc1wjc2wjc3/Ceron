"use client";

import Link from "next/link";
import { Box, Divider, Grid, Stack, Typography } from "@mui/material";
import HubIcon from "@mui/icons-material/Hub";

const COLUMNS = [
  {
    title: "Platform",
    items: [
      { label: "Product capabilities", href: "/products" },
      { label: "Architecture", href: "/products#architecture" },
      { label: "Console", href: "/app" },
    ],
  },
  {
    title: "Compliance",
    items: [
      { label: "Ongoing monitoring", href: "/app/compliance" },
      { label: "SAR filing (JFIU)", href: "/app/compliance" },
      { label: "Regulatory MI", href: "/app/compliance" },
    ],
  },
  {
    title: "Company",
    items: [
      { label: "GitHub", href: "https://github.com" },
      { label: "Contact", href: "mailto:hello@ceron.ai" },
    ],
  },
];

export default function SiteFooter() {
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
              Underwriting and compliance automation built for Hong Kong financial institutions.
            </Typography>
          </Grid>
          {COLUMNS.map((c) => (
            <Grid item xs={6} md={2.66} key={c.title}>
              <Typography variant="caption" fontWeight={700} color="text.secondary">
                {c.title.toUpperCase()}
              </Typography>
              <Stack spacing={1} sx={{ mt: 2 }}>
                {c.items.map((i) => (
                  <Typography
                    key={i.label}
                    variant="body2"
                    component={Link}
                    href={i.href}
                    sx={{ textDecoration: "none", color: "text.primary", "&:hover": { color: "primary.main" } }}
                  >
                    {i.label}
                  </Typography>
                ))}
              </Stack>
            </Grid>
          ))}
        </Grid>
        <Divider sx={{ my: 4 }} />
        <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" spacing={1}>
          <Typography variant="caption" color="text.secondary">
            © {new Date().getFullYear()} Ceron · Built in Hong Kong · Data residency PDPO aligned
          </Typography>
          <Typography variant="caption" color="text.secondary">
            SFC · HKMA · MPFA · IRD compliance gates
          </Typography>
        </Stack>
      </Box>
    </Box>
  );
}
