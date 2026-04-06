import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Login",
  description: "Secure sign in to AI-Analyst Platform.",
  alternates: {
    canonical: "/login",
  },
};

export default function LoginLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return children;
}
