// Thin client for the Lumina API. The browser only ever talks to our backend.
const BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type Preset = {
  id: string;
  label: string;
  category: string;
  capability: string;
  credit_cost: number;
};

export type Asset = {
  id: string;
  kind: string;
  cdn_url: string;
  thumbnail_url: string | null;
};

export type Job = {
  id: string;
  status: "queued" | "running" | "succeeded" | "failed" | "canceled";
  capability: string;
  preset_id: string | null;
  provider: string | null;
  model: string | null;
  credit_cost: number;
  error_code: string | null;
  created_at: string;
  finished_at: string | null;
  assets: Asset[];
};

export async function listPresets(): Promise<Preset[]> {
  const r = await fetch(`${BASE}/v1/presets`, { cache: "no-store" });
  if (!r.ok) throw new Error("failed to load presets");
  return r.json();
}

export async function createGeneration(input: {
  preset_id: string;
  prompt: string;
  image_url?: string;
  enhance_prompt?: boolean;
  examples?: string[];
}): Promise<Job> {
  const r = await fetch(`${BASE}/v1/generations`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!r.ok) throw new Error(`generation failed: ${r.status}`);
  return r.json();
}

export async function getGeneration(id: string): Promise<Job> {
  const r = await fetch(`${BASE}/v1/generations/${id}`, { cache: "no-store" });
  if (!r.ok) throw new Error("failed to load job");
  return r.json();
}
