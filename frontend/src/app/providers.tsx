"use client";

import { ThemeProvider, CssBaseline, createTheme } from "@mui/material";
import { AuthProvider } from "../components/AuthProvider";

// 美系 SaaS 设计语言：极致留白、深色近黑的正文、单一强调色、圆角胶囊按钮、
// 无正文阴影而强调分割线，字体走系统 sans（含 PingFang / Microsoft YaHei 兜底）。
const theme = createTheme({
  palette: {
    mode: "light",
    background: { default: "#ffffff", paper: "#ffffff" },
    text: { primary: "#0b1220", secondary: "#5a6472" },
    primary: { main: "#1f4dff" },
    divider: "#e6e9ef",
  },
  shape: { borderRadius: 10 },
  typography: {
    fontFamily:
      "Inter, ui-sans-serif, system-ui, -apple-system, 'Segoe UI', 'PingFang HK', 'Microsoft YaHei', Roboto, Helvetica, Arial, sans-serif",
    h1: { fontWeight: 800, letterSpacing: "-0.03em", fontSize: "clamp(2.5rem, 5vw, 4.25rem)", lineHeight: 1.05 },
    h2: { fontWeight: 800, letterSpacing: "-0.025em", fontSize: "clamp(2rem, 3.6vw, 3rem)", lineHeight: 1.12 },
    h3: { fontWeight: 700, letterSpacing: "-0.02em", fontSize: "clamp(1.5rem, 2.4vw, 2.125rem)", lineHeight: 1.2 },
    h4: { fontWeight: 700, letterSpacing: "-0.02em" },
    h6: { fontWeight: 700, letterSpacing: "-0.01em" },
    button: { textTransform: "none", fontWeight: 650 },
    subtitle1: { fontWeight: 600 },
    body1: { lineHeight: 1.65 },
    body2: { lineHeight: 1.6 },
  },
  components: {
    MuiButton: {
      defaultProps: { disableElevation: true },
      styleOverrides: { root: { borderRadius: 999, paddingInline: 22 } },
    },
    MuiChip: { styleOverrides: { root: { borderRadius: 6, fontWeight: 600 } } },
    MuiAppBar: { defaultProps: { elevation: 0 } },
    MuiPaper: { defaultProps: { elevation: 0 } },
    MuiCard: { defaultProps: { elevation: 0 } },
  },
});

export default function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <AuthProvider>{children}</AuthProvider>
    </ThemeProvider>
  );
}
