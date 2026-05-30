export default function Home() {
  return (
    <div>
      <h1>Lumina</h1>
      <p style={{ color: "#b6b6c4", lineHeight: 1.6 }}>
        A Higgsfield-style AI media studio: cinematic text/image-to-video with
        camera-motion presets, built on hosted model APIs.
      </p>
      <a
        href="/studio"
        style={{
          display: "inline-block",
          marginTop: 16,
          padding: "10px 18px",
          background: "#6c5cff",
          color: "white",
          borderRadius: 8,
          textDecoration: "none",
        }}
      >
        Open Studio →
      </a>
    </div>
  );
}
