import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "AI-Analyst Platform",
    short_name: "AI-Analyst",
    description: "Premium control center for personal finance discipline, fraud defense and moderated blacklist intelligence.",
    start_url: "/",
    display: "standalone",
    background_color: "#f4f1ea",
    theme_color: "#111111",
    lang: "ru",
    icons: [
      {
        src: "/icon.svg",
        sizes: "any",
        type: "image/svg+xml",
      },
    ],
  };
}
