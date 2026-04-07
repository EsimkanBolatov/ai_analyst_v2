import type { Metadata } from "next";

import { LegacyShell } from "@/components/legacy/legacy-shell";
import { SessionGuard } from "@/components/session-guard";

export const metadata: Metadata = {
  title: "ML Lab",
  description: "Migrated Streamlit analytics workflows: profiling, AI report, model training, prediction and fraud checking.",
  alternates: {
    canonical: "/ml-lab",
  },
};

export default function MlLabLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <SessionGuard>
      <LegacyShell>{children}</LegacyShell>
    </SessionGuard>
  );
}
