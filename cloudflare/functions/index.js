// Per-page SEO and link previews for "/" (Cloudflare Pages Function).
// The page is a single HTML file; this rewrites its <head> on the way out so crawlers (X, Google, Slack…)
// see the right title, description and share image for a replay link, or the latest race on the home page.
// RH_ORIGIN (Pages variable/secret) = the race server; RH_SITE = this site's public URL
const DEFAULT_SITE = "https://airabbithole.pages.dev";

const fmt = x => (x < 60 ? `${(Math.floor(x * 10) / 10).toFixed(1)} s` : `${Math.floor(x / 60)}:${(x % 60).toFixed(1).padStart(4, "0")}`);

async function summary(ORIGIN, id) {
  if (!ORIGIN) return null;
  try {
    const path = id ? `/api/runs/${encodeURIComponent(id)}/summary` : "/api/featured";
    const r = await fetch(ORIGIN + path, { cf: { cacheTtl: id ? 3600 : 60, cacheEverything: true }, signal: AbortSignal.timeout(1500) });
    return r.ok ? await r.json() : null;
  } catch { return null; }
}

export async function onRequestGet(ctx) {
  const res = await ctx.next();
  const ORIGIN = (ctx.env.RH_ORIGIN || "").replace(/\/$/, ""), SITE = (ctx.env.RH_SITE || DEFAULT_SITE).replace(/\/$/, "");
  if (!(res.headers.get("content-type") || "").includes("text/html")) return res;
  const url = new URL(ctx.request.url);
  const id = url.searchParams.get("replay") || url.searchParams.get("answer");
  const s = await summary(ORIGIN, id);
  const cb = s && s.lanes && s.lanes.cerebras;
  let title = null, desc = null, canon = `${SITE}/`, image = `${SITE}/api/og.png${cb ? `?v=${encodeURIComponent(s.id)}` : ""}`, alt = null;
  if (id && cb) {
    const g = s.lanes.gpu, o = (s.outcome || {}).gpu;
    const gpu = g ? `, the same model on GPUs took ${fmt(g.seconds)}` : o === "lane_timeout" ? ", the same model on GPUs was still thinking at 5 minutes" : "";
    title = `${s.start} → ${s.target} in ${fmt(cb.seconds)} · Rabbit Hole`;
    desc = `${cb.path.join(" → ")}. Kimi K3.1 Pro on Cerebras found it in ${fmt(cb.seconds)}${gpu}. Watch the replay.`;
    canon = `${SITE}/?replay=${encodeURIComponent(s.id)}`;
    image = `${SITE}/api/og.png?run=${encodeURIComponent(s.id)}`;
    alt = `How is ${s.start} connected to ${s.target}? ${cb.path.join(" → ")}`;
  }
  const set = v => ({ element(e) { if (v != null) e.setAttribute("content", v); } });
  return new HTMLRewriter()
    .on("title", { element(e) { if (title) e.setInnerContent(title); } })
    .on('meta[name="description"], meta[property="og:description"], meta[name="twitter:description"]', set(desc))
    .on('meta[property="og:title"], meta[name="twitter:title"]', set(title))
    .on('meta[property="og:url"]', set(canon))
    .on('link[rel="canonical"]', { element(e) { e.setAttribute("href", canon); } })
    .on('meta[property="og:image"], meta[name="twitter:image"]', set(image))
    .on('meta[property="og:image:alt"], meta[name="twitter:image:alt"]', set(alt))
    .transform(res);
}
