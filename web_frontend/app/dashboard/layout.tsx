import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Dashboard",
  description: "Protected workspace for personal budget control, statement import, AI accountant chat and fraud report submission.",
  alternates: {
    canonical: "/dashboard",
  },
};

export default function DashboardLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return children;
}
