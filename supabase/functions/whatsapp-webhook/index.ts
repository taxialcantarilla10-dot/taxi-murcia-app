import "jsr:@supabase/functions-js/edge-runtime.d.ts";

const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

async function saveSession(phone: string, message: any) {
  const url = Deno.env.get("SUPABASE_URL")!;
  const key = Deno.env.get("SERVICE_ROLE_KEY")!;
  const text = message?.text?.body ?? "";
  const loc = message?.location;
  const row: Record<string, unknown> = { phone, state: "awaiting_origin" };
  if (text) row.origin_address = text;
  if (loc) { row.origin_lat = loc.latitude; row.origin_lng = loc.longitude; }
  const r = await fetch(`${url}/rest/v1/whatsapp_sessions?on_conflict=phone`, { method: "POST", headers: { apikey: key, Authorization: `Bearer ${key}`, "Content-Type": "application/json", Prefer: "resolution=merge-duplicates,return=minimal" }, body: JSON.stringify(row) });
  if (!r.ok) console.error("session save failed", r.status, await r.text());
}

Deno.serve(async (req) => {
  const u = new URL(req.url);
  if (req.method === "GET") {
    if (u.searchParams.get("hub.mode") === "subscribe" && u.searchParams.get("hub.verify_token") === "taximurcia-final") return new Response(u.searchParams.get("hub.challenge") ?? "", { status: 200 });
    return new Response("Forbidden", { status: 403 });
  }
  if (req.method !== "POST") return json({ ok: false }, 405);
  try {
    const payload = await req.json();
    for (const entry of payload.entry ?? []) for (const change of entry.changes ?? []) for (const message of change.value?.messages ?? []) if (message.from) await saveSession(message.from, message);
    return json({ ok: true });
  } catch (e) { console.error(e); return json({ ok: false }, 500); }
});
