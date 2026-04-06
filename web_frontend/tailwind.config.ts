import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        paper: "#f4f1ea",
        ink: "#111111",
        smoke: "#69645c",
        line: "#d0cbc2",
        panel: "#fbf8f2",
        accent: "#1f1f1f",
      },
      boxShadow: {
        premium: "0 24px 80px rgba(17, 17, 17, 0.12)",
      },
      backgroundImage: {
        grain:
          "radial-gradient(circle at top, rgba(17,17,17,0.06), transparent 36%), linear-gradient(135deg, rgba(255,255,255,0.3), rgba(17,17,17,0.03))",
      },
      maxWidth: {
        shell: "1200px",
      },
    },
  },
  plugins: [],
};

export default config;
