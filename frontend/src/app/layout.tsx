import type { Metadata } from "next";
import Providers from "./providers";

export const metadata: Metadata = {
  title: "Ceron 控制台",
  description: "Heron 产品的香港金融业本土化前端",
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
