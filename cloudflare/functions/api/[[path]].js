// Proxies /api/* to the Rabbit Hole server on the Oracle VM, keeping the page and API on one clean origin.
// The visitor's IP goes along in a header the server trusts only with the shared secret (for per-visitor limits).
// RH_ORIGIN (a Pages variable/secret) is the race server, e.g. https://your-server.example.com
export async function onRequest({ request, env }) {
  const ORIGIN = (env.RH_ORIGIN || "").replace(/\/$/, "");
  if (!ORIGIN) return new Response("RH_ORIGIN is not set", { status: 500 });
  const url = new URL(request.url);
  const headers = new Headers(request.headers);
  headers.set("x-rh-client-ip", request.headers.get("cf-connecting-ip") || "");
  headers.set("x-rh-proxy", env.RH_PROXY_SECRET || "");
  headers.delete("host");
  const upstream = await fetch(ORIGIN + url.pathname + url.search, {
    method: request.method, headers,
    body: ["GET", "HEAD"].includes(request.method) ? undefined : request.body,
    redirect: "manual",
  });
  return new Response(upstream.body, upstream);  // streams server-sent events straight through
}
