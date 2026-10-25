"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import {
  AppBar, Box, Button, Chip, IconButton, Menu, MenuItem, Toolbar, Typography,
} from "@mui/material";
import AccountCircleIcon from "@mui/icons-material/AccountCircle";
import { LanguageSwitcher, useT } from "../app/i18n";
import { useAuth } from "./AuthProvider";

const LINKS = [
  { href: "/app", key: "navWorkspace" },
  { href: "/app/agent", key: "navAgent" },
  { href: "/app/compliance", key: "navCompliance" },
  { href: "/app/models", key: "navModels" },
  { href: "/products", key: "navProducts" },
];

export default function NavBar() {
  const { t } = useT();
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const [health, setHealth] = useState<any>(null);
  const [anchor, setAnchor] = useState<null | HTMLElement>(null);

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
          href="/app"
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
                sx={{ color: active ? "primary.main" : "text.primary", fontWeight: active ? 700 : 400 }}
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
        {user ? (
          <>
            <IconButton size="small" onClick={(e) => setAnchor(e.currentTarget)} sx={{ ml: 1 }}>
              <AccountCircleIcon />
            </IconButton>
            <Menu anchorEl={anchor} open={Boolean(anchor)} onClose={() => setAnchor(null)}>
              <MenuItem disabled sx={{ fontSize: 13, color: "text.secondary" }}>
                {user.email}
              </MenuItem>
              <MenuItem
                onClick={() => {
                  setAnchor(null);
                  logout();
                }}
              >
                {t("navLogout")}
              </MenuItem>
            </Menu>
          </>
        ) : (
          <Button component={Link} href="/login" variant="contained" size="small" sx={{ ml: 1 }}>
            {t("signIn")}
          </Button>
        )}
      </Toolbar>
    </AppBar>
  );
}
