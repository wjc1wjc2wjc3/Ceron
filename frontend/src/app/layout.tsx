import type { Metadata } from "next";
import Providers from "./providers";

export const metadata: Metadata = {
  title: "Ceron 控制台",
  description: "香港金融业承保与合规自动化前端控制台",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-HK">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
