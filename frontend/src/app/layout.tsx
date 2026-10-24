import type { Metadata } from "next";
import { cookies } from "next/headers";
import Providers from "./providers";
import { DEFAULT_LOCALE, htmlLang, metaFor } from "./i18n-meta";

// 语言写在 cookie（ceron.locale）里，服务端据此输出对应语言的 title / description / lang，
// 让分享链接与爬虫拿到的是当前语言版本的元数据。
export async function generateMetadata(): Promise<Metadata> {
  const locale = cookies().get("ceron.locale")?.value || DEFAULT_LOCALE;
  const meta = metaFor(locale);
  return {
    title: meta.title,
    description: meta.description,
  };
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const locale = cookies().get("ceron.locale")?.value || DEFAULT_LOCALE;
  return (
    <html lang={htmlLang(locale)}>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
