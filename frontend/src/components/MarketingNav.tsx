"use client";

import Link from "next/link";
import { AppBar, Box, Button, Stack, Toolbar, Typography } from "@mui/material";
import HubIcon from "@mui/icons-material/Hub";
import { LanguageSwitcher, useT } from "../app/i18n";
import { useAuth } from "./AuthProvider";

/** 营销页顶部导航（对 herondata.io 的 nav：品牌 + 少量栏目 + 右侧双 CTA）。 */
export default function MarketingNav() {
  const { t } = useT();
  const { user } = useAuth();

  const links = [
    { key: "navPlatform", href: "/products" },
    { key: "navArchitecture", href: "/products#architecture" },
  ];

  return (
    <AppBar
      position="static"
      color="transparent"
      elevation={0}
      sx={{ borderBottom: 1, borderColor: "divider", bgcolor: "background.paper" }}
    >
      <Toolbar sx={{ gap: 2, maxWidth: 1180, mx: "auto", width: "100%", px: { xs: 2.5, md: 4 } }}>
        <Typography
          variant="h6"
          component={Link}
          href="/"
          sx={{ textDecoration: "none", color: "text.primary", fontWeight: 800, letterSpacing: "-0.02em" }}
        >
          <Stack direction="row" spacing={1} alignItems="center">
            <HubIcon sx={{ color: "primary.main" }} />
            Ceron
          </Stack>
        </Typography>
        <Box sx={{ display: { xs: "none", md: "flex" }, gap: 2, ml: 3 }}>
          {links.map((l) => (
            <Button
              key={l.href}
              component={Link}
              href={l.href}
              sx={{ color: "text.primary", fontWeight: 500 }}
            >
              {t(l.key)}
            </Button>
          ))}
        </Box>
        <Box sx={{ flexGrow: 1 }} />
        <LanguageSwitcher />
        {user ? (
          <Button component={Link} href="/app" variant="contained" sx={{ ml: 1.5 }}>
            {t("navOpenConsole")}
          </Button>
        ) : (
          <>
            <Button component={Link} href="/login" sx={{ ml: 1.5, color: "text.primary" }}>
              {t("navLogIn")}
            </Button>
            <Button component={Link} href="/register" variant="contained">
              {t("navStartFree")}
            </Button>
          </>
        )}
      </Toolbar>
    </AppBar>
  );
}
