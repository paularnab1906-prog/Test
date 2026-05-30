import type { ReactNode } from "react";

export const metadata = {
  title: "Lumina — AI Media Studio",
  description: "Cinematic AI video and image generation",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body
        style={{
          margin: 0,
          fontFamily: "system-ui, sans-serif",
          background: "#0b0b10",
          color: "#f4f4f7",
        }}
      >
        <header style={{ padding: "16px 24px", borderBottom: "1px solid #23232e" }}>
          <strong style={{ fontSize: 18 }}>Lumina</strong>
          <span style={{ marginLeft: 8, color: "#8a8a9a" }}>AI Media Studio</span>
        </header>
        <main style={{ maxWidth: 760, margin: "0 auto", padding: 24 }}>{children}</main>
      </body>
    </html>
  );
}
