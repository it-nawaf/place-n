// place.n live calendar — Cloudflare Worker
// Reads each apartment's Gathern / Airbnb calendar links from https://place-n.com/data.json
// and returns the booked nights right now, so the site shows new bookings within minutes.
//   GET https://placen-cal.blue-hill-91f0.workers.dev/          -> {updated, apts: {id: ["YYYY-MM-DD", ...]}, failed: [...]}
//   GET https://placen-cal.blue-hill-91f0.workers.dev/?id=abc   -> same, for one apartment

const SITE = "https://place-n.com";
const ALLOWED = ["https://place-n.com", "https://www.place-n.com", "https://it-nawaf.github.io"];
const FEED_CACHE = 120;   // seconds a calendar feed is reused
const DATA_CACHE = 300;   // seconds data.json is reused

export default {
  async fetch(request) {
    const origin = request.headers.get("Origin") || "";
    const cors = {
      "Access-Control-Allow-Origin": ALLOWED.includes(origin) ? origin : SITE,
      "Access-Control-Allow-Methods": "GET, OPTIONS",
      "Vary": "Origin",
    };
    if (request.method === "OPTIONS") return new Response(null, { headers: cors });
    if (request.method !== "GET") return new Response("Method not allowed", { status: 405, headers: cors });

    const url = new URL(request.url);
    const only = url.searchParams.get("id");
    try {
      const data = await (await fetch(`${SITE}/data.json`, { cf: { cacheTtl: DATA_CACHE, cacheEverything: true } })).json();
      const apts = (data.apts || []).filter(a => !only || a.id === only);
      const cutoff = riyadhDate(-7);
      const out = {}, failed = [];
      await Promise.all(apts.map(async a => {
        const links = [a.ical, a.ical2].filter(u => typeof u === "string" && u.startsWith("https://"));
        if (!links.length) return;
        const sets = await Promise.all(links.map(readFeed));
        const good = sets.filter(Boolean);
        if (!good.length) { failed.push(a.id); return; }
        const all = new Set();
        good.forEach(s => s.forEach(d => { if (d >= cutoff) all.add(d); }));
        out[a.id] = [...all].sort();
      }));
      return Response.json({ updated: new Date().toISOString(), apts: out, failed }, {
        headers: { ...cors, "Cache-Control": "public, max-age=60" },
      });
    } catch (e) {
      return Response.json({ error: "unavailable" }, { status: 502, headers: cors });
    }
  },
};

// Gathern serves an old cached copy of a calendar link for hours. Spelling the address a
// little differently every 2 minutes (percent-encoding one character, which points to the
// same file) gets a fresh copy each time.
function fresh(link) {
  const u = new URL(link);
  const m = u.pathname.match(/^(.*\/)([^/]+)(\.ics)$/);
  const bucket = Math.floor(Date.now() / 120000);
  if (m && u.hostname.endsWith("gathern.co")) {
    const name = decodeURIComponent(m[2]);
    const i = bucket % name.length, j = (i + 1 + Math.floor(bucket / name.length) % (name.length - 1)) % name.length;
    const spelled = [...name].map((c, k) => (k === i || k === j) ? "%" + c.charCodeAt(0).toString(16).toUpperCase().padStart(2, "0") : c).join("");
    u.pathname = m[1] + spelled + m[3];
  }
  u.searchParams.set("_", String(bucket));
  return u.toString();
}

async function readFeed(link) {
  try {
    const r = await fetch(fresh(link), {
      headers: { "User-Agent": "Mozilla/5.0 (compatible; place-n-calendar/1.0)" },
      cf: { cacheTtl: FEED_CACHE, cacheEverything: true },
    });
    if (!r.ok) return null;
    return nights(await r.text());
  } catch (e) {
    return null;
  }
}

// Booked nights in an iCalendar text: every date from DTSTART up to (not including) DTEND.
function nights(ics) {
  if (!ics.includes("BEGIN:VCALENDAR")) return null;
  const text = ics.replace(/\r?\n[ \t]/g, "");
  const out = new Set();
  for (const ev of text.split("BEGIN:VEVENT").slice(1)) {
    const s = ev.match(/^DTSTART[^:\n]*:(\d{8})/m);
    if (!s) continue;
    const e = ev.match(/^DTEND[^:\n]*:(\d{8})/m);
    let d = toDate(s[1]);
    const end = e ? toDate(e[1]) : new Date(d.getTime() + 864e5);
    for (let i = 0; d < end && i < 400; i++) {
      out.add(d.toISOString().slice(0, 10));
      d = new Date(d.getTime() + 864e5);
    }
  }
  return out;
}

function toDate(s) {
  return new Date(Date.UTC(+s.slice(0, 4), +s.slice(4, 6) - 1, +s.slice(6, 8)));
}

function riyadhDate(offsetDays) {
  const t = new Date(Date.now() + 3 * 3600e3 + offsetDays * 864e5);
  return t.toISOString().slice(0, 10);
}
