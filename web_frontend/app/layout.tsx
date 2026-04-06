import type { Metadata, Viewport } from "next";
import { IBM_Plex_Mono, Manrope } from "next/font/google";

import "@/app/globals.css";
import { Header } from "@/components/header";
import { getSiteUrl } from "@/lib/site";

const manrope = Manrope({
  subsets: ["latin", "cyrillic"],
  variable: "--font-manrope",
});

const mono = IBM_Plex_Mono({
  subsets: ["latin", "cyrillic"],
  weight: ["400", "500"],
  variable: "--font-mono",
});

const siteUrl = getSiteUrl();

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: {
    default: "AI-Analyst Platform",
    template: "%s | AI-Analyst Platform",
  },
  description: "Premium control center for personal finance discipline, fraud defense, moderated blacklist intelligence and browser-side protection.",
  applicationName: "AI-Analyst Platform",
  keywords: [
    "AI fraud detection",
    "personal finance assistant",
    "budget control",
    "moderation queue",
    "browser protection",
    "FastAPI",
    "Next.js",
  ],
  authors: [{ name: "AI-Analyst Platform Team" }],
  creator: "AI-Analyst Platform",
  publisher: "AI-Analyst Platform",
  category: "finance",
  alternates: {
    canonical: "/",
  },
  openGraph: {
    type: "website",
    url: siteUrl,
    title: "AI-Analyst Platform",
    description: "Premium control center for personal finance discipline, fraud defense and moderated blacklist intelligence.",
    siteName: "AI-Analyst Platform",
    locale: "ru_RU",
    images: [
      {
        url: "/og-image.svg",
        width: 1200,
        height: 630,
        alt: "AI-Analyst Platform",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "AI-Analyst Platform",
    description: "Personal finance control, AI accountant, moderation workflow and browser fraud defense.",
    images: ["/og-image.svg"],
  },
  icons: {
    icon: "/icon.svg",
    shortcut: "/icon.svg",
    apple: "/icon.svg",
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#111111",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ru">
      <body
        className={`${manrope.variable} ${mono.variable} font-[family-name:var(--font-manrope)]`}
      >
        <Header />
        <main className="pb-16">{children}</main>
      </body>
    </html>
  );
}
