import { CssBaseline, ThemeProvider, createTheme } from "@mui/material";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Ceron 控制台",
  description: "Heron 产品的香港金融业本土化前端",
};

const theme = createTheme({ palette: { mode: "light" } });

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-HK">
      <body>
        <ThemeProvider theme={theme}>
          <CssBaseline />
          {children}
        </ThemeProvider>
      </body>
    </html>
  );
}
