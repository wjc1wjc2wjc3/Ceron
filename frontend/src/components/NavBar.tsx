"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { AppBar, Box, Button, Chip, Toolbar, Typography } from "@mui/material";
import { LanguageSwitcher, useT } from "../app/i18n";

const LINKS = [
  { href: "/", key: "navWorkspace" },
  { href: "/compliance", key: "navCompliance" },
  { href: "/products", key: "navProducts" },
];

export default function NavBar() {
  const { t } = useT();
  const pathname = usePathname();
  const [health, setHealth] = useState<any>(null);

  useEffect(() => {
    fetch("/api/health")
      .then((r) => r.json())
      .then(setHealth)
      .catch(() => setHealth({ status: "error" }));
  }, []);

  return (
    <AppBar
      position="static"
      color="transparent"
      elevation={0}
      sx={{ borderBottom: 1, borderColor: "divider", mb: 3, bgcolor: "background.paper" }}
    >
      <Toolbar sx={{ gap: 1 }}>
        <Typography
          variant="h6"
          component={Link}
          href="/"
          sx={{ textDecoration: "none", color: "primary.main", fontWeight: 700, mr: 2 }}
        >
          Ceron
        </Typography>
        <Box sx={{ display: "flex", gap: 0.5 }}>
          {LINKS.map((l) => {
            const active = pathname === l.href;
            return (
              <Button
                key={l.href}
                component={Link}
                href={l.href}
                sx={{
                  color: active ? "primary.main" : "text.primary",
                  fontWeight: active ? 700 : 400,
                }}
              >
                {t(l.key)}
              </Button>
            );
          })}
        </Box>
        <Box sx={{ flexGrow: 1 }} />
        <Chip
          size="small"
          label={`${t("gateway")}：${health?.status ?? "…"}`}
          color={health?.status === "ok" ? "success" : "default"}
          sx={{ mr: 2 }}
        />
        <LanguageSwitcher />
      </Toolbar>
    </AppBar>
  );
}
