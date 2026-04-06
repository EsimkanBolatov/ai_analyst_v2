import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Moderation",
  description: "Protected moderation board for AI-assisted fraud triage, human resolution and blacklist curation.",
  alternates: {
    canonical: "/moderation",
  },
};

export default function ModerationLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return children;
}
