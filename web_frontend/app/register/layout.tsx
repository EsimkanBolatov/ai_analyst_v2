import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Register",
  description: "Create an AI-Analyst Platform account for budget control and fraud reporting.",
  alternates: {
    canonical: "/register",
  },
};

export default function RegisterLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return children;
}
