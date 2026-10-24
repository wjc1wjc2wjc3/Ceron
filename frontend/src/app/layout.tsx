import type { Metadata } from "next";
import Providers from "./providers";

export const metadata: Metadata = {
  title: "Ceron — Underwriting automation for Hong Kong finance",
  description:
    "Ceron turns raw submissions into auditable decisions for Hong Kong insurance, trusts and family offices: bilingual extraction, ICRIS / credit bureau enrichment, and SFC / HKMA / MPFA compliance gates.",
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
