import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "천재따소미 | DCS 유지보수 AI 챗봇",
  description: "발전소 전산/DCS 유지보수 지원 AI 챗봇",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=Geist:wght@500;600&family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="bg-background text-on-background font-body-base">{children}</body>
    </html>
  );
}
