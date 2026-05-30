"use client";

import { useEffect, useState } from "react";
import {
  createGeneration,
  getGeneration,
  listPresets,
  type Job,
  type Preset,
} from "@/lib/api";

export default function Studio() {
  const [presets, setPresets] = useState<Preset[]>([]);
  const [presetId, setPresetId] = useState("");
  const [prompt, setPrompt] = useState("");
  const [imageUrl, setImageUrl] = useState("");
  const [enhance, setEnhance] = useState(false);
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    listPresets()
      .then((p) => {
        setPresets(p);
        if (p[0]) setPresetId(p[0].id);
      })
      .catch((e) => setError(String(e)));
  }, []);

  // Poll the job until it reaches a terminal state. (Phase 1 uses polling;
  // Architecture calls for SSE/WebSocket as a later upgrade.)
  useEffect(() => {
    if (!job || job.status === "succeeded" || job.status === "failed") return;
    const t = setTimeout(async () => {
      try {
        setJob(await getGeneration(job.id));
      } catch (e) {
        setError(String(e));
      }
    }, 1500);
    return () => clearTimeout(t);
  }, [job]);

  async function submit() {
    setError("");
    try {
      setJob(
        await createGeneration({
          preset_id: presetId,
          prompt,
          image_url: imageUrl || undefined,
          enhance_prompt: enhance,
        }),
      );
    } catch (e) {
      setError(String(e));
    }
  }

  const field: React.CSSProperties = {
    width: "100%",
    padding: 10,
    marginTop: 6,
    background: "#15151d",
    border: "1px solid #2a2a36",
    borderRadius: 8,
    color: "#f4f4f7",
    boxSizing: "border-box",
  };

  return (
    <div>
      <h1>Studio</h1>

      <label>
        Preset
        <select style={field} value={presetId} onChange={(e) => setPresetId(e.target.value)}>
          {presets.map((p) => (
            <option key={p.id} value={p.id}>
              {p.label} — {p.credit_cost} credits
            </option>
          ))}
        </select>
      </label>

      <label style={{ display: "block", marginTop: 16 }}>
        Prompt
        <textarea
          style={{ ...field, minHeight: 80 }}
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="a fox running through a neon city at night"
        />
      </label>

      <label style={{ display: "block", marginTop: 16 }}>
        Image URL (for image-to-video presets)
        <input style={field} value={imageUrl} onChange={(e) => setImageUrl(e.target.value)} />
      </label>

      <label style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 16 }}>
        <input type="checkbox" checked={enhance} onChange={(e) => setEnhance(e.target.checked)} />
        Enhance prompt with AI (OpenRouter)
      </label>

      <button
        onClick={submit}
        disabled={!prompt || !presetId}
        style={{
          marginTop: 20,
          padding: "10px 18px",
          background: "#6c5cff",
          color: "white",
          border: "none",
          borderRadius: 8,
          cursor: "pointer",
        }}
      >
        Generate
      </button>

      {error && <p style={{ color: "#ff6b6b" }}>{error}</p>}

      {job && (
        <div style={{ marginTop: 28, padding: 16, background: "#15151d", borderRadius: 12 }}>
          <div>
            Job <code>{job.id.slice(0, 8)}</code> — <strong>{job.status}</strong>
          </div>
          {job.error_code && <div style={{ color: "#ff6b6b" }}>{job.error_code}</div>}
          {job.assets.map((a) =>
            a.kind === "image" ? (
              <img
                key={a.id}
                src={a.cdn_url}
                alt="generated"
                style={{ width: "100%", marginTop: 12, borderRadius: 8 }}
              />
            ) : (
              <video
                key={a.id}
                src={a.cdn_url}
                poster={a.thumbnail_url ?? undefined}
                controls
                style={{ width: "100%", marginTop: 12, borderRadius: 8 }}
              />
            ),
          )}
        </div>
      )}
    </div>
  );
}
