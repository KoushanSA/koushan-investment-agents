// Chrome fallback for البورصة العقارية — only when the cloud run exits 3 on an MOJ host.
// Run with Claude in Chrome's javascript tool in a tab open at https://srem.moj.gov.sa/
// (same-origin for the API's CORS). Paste this whole file as the code, with SEEDS replaced by
// the JSON array from $RUN/seeds.json. It runs in the background (calls time out at 45 s);
// poll window.__srem.done, then read window.__srem.chunks[i] one by one and append each to
// $RUN/srem.json.part in order; `python3 srem_assemble.py` turns the parts into srem.json.
window.__srem = { done: false, chunks: [], progress: 0 };
(async () => {
  const SEEDS = __SEEDS__;
  const B = 'https://prod-srem-api-srem.moj.gov.sa/api/v1/Dashboard/GetAreaInfo';
  const U = 'https://prod-inquiryservice-srem.moj.gov.sa/api/v1/AddressInfo/SearchAddress';
  const JED = 37528, sleep = ms => new Promise(r => setTimeout(r, ms));
  const area = async (t, s, n = 8) => { for (let i = 0; i < n; i++) { const r = await fetch(B, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ periodCategory: 'W', period: 1, areaType: t, areaSerial: s, cityCode: JED }) }).then(r => r.json()).catch(() => ({})); if (r.IsSuccess && r.Data) return [r.Data, i + 1]; await sleep(1500); } return [null, n]; };
  const out = { source: 'البورصة العقارية', fetched_at: new Date().toISOString(), period: 'W', city_code: JED, via: 'chrome', gates: [], districts: [] };
  const [city, att] = await area('C', JED);
  if (!city) { window.__srem.chunks = [JSON.stringify({ error: 'city query failed' })]; window.__srem.sums = window.__srem.chunks.map(x => { let h = 0; for (let k = 0; k < x.length; k++) h = (h + (k + 1) * x.charCodeAt(k)) % 1000000007; return h; }); window.__srem.done = true; return; }
  out.total = city.Total; out.daily = city.Stats; out.ticker = city.Transactions; out.city_attempts = att;
  const gaz = new Map();
  for (const n of SEEDS) {
    const base = n.replace(/^حي /, '').replace(/-/g, ' ');
    for (const v of [...new Set(['حي ' + base, base, base.replace(/ة/g, 'ه'), base.replace(/^ال/, '')])]) {
      let e = []; try { const r = await fetch(U + '?' + new URLSearchParams({ Term: v })).then(r => r.json()); e = (r?.Data?.Entities || []).filter(x => x.CityCode === JED && x.DistrictCode); } catch (x) {}
      e.forEach(x => gaz.set(x.DistrictCode, x.DistrictName)); if (e.length) break;
    }
  }
  out.gazetteer = Object.fromEntries([...gaz.entries()].map(([k, v]) => [String(k), v]));
  out.district_failures = [];
  // three at a time: the API times out often, and serial polling of ~110 districts took ~35 min
  const q = [...gaz.entries()];
  const worker = async () => { while (q.length) { const [code, name] = q.shift();
    const [d, a] = await area('D', code, 5); window.__srem.progress++;
    if (!d) { out.district_failures.push({ code, name }); continue; }
    const t = d.Total || {};
    out.districts.push({ code, name, count: t.Count || 0, value: t.TotalPrices || 0, area: t.TotalAreas || 0, avg_ppm: t.AveragePrice ?? null, min_ppm: t.MinPrice ?? null, max_ppm: t.MaxPrice ?? null, attempts: a });
    await sleep(300); } };
  await Promise.all([worker(), worker(), worker()]);
  // one retry pass for districts that never answered
  const retry = out.district_failures.splice(0); for (const f of retry) { const [d, a] = await area('D', f.code, 6);
    if (!d) { out.district_failures.push(f); continue; } const t = d.Total || {};
    out.districts.push({ code: f.code, name: f.name, count: t.Count || 0, value: t.TotalPrices || 0, area: t.TotalAreas || 0, avg_ppm: t.AveragePrice ?? null, min_ppm: t.MinPrice ?? null, max_ppm: t.MaxPrice ?? null, attempts: a }); }
  // compact hand-over (v1): the javascript tool truncates output near 1,000 chars, so keep it small.
  const T = out.total;
  const c = { v: 1, at: out.fetched_at, ca: out.city_attempts,
    t: [T.Count, T.TotalPrices, T.TotalAreas, T.AveragePrice, T.MinPrice, T.MaxPrice, T.BestBid, T.BestAsk],
    d: (out.daily || []).map(x => [x.AggregationDate.slice(0, 10), x.AreaSerial, x.TotalCount, x.TotalPrice, x.TotalArea, x.AveragePrice]),
    k: (out.ticker || []).map(x => [x.Id, x.TransAmount, x.TransDate, x.TransArea, x.CityName, x.NHName, x.Plan, x.LandNumber, x.UnitType]),
    r: out.districts.filter(x => x.count > 0).map(x => [x.code, x.name, x.count, x.value, x.area]),
    z: out.districts.filter(x => !x.count).map(x => x.code),
    f: out.district_failures.map(x => x.code) };
  const s = JSON.stringify(c);
  for (let i = 0; i < s.length; i += 800) window.__srem.chunks.push(s.slice(i, i + 800));
  // integrity check for the hand-over: position-weighted code-point sum per chunk (srem_assemble.py recomputes it)
  window.__srem.sums = window.__srem.chunks.map(x => { let h = 0; for (let k = 0; k < x.length; k++) h = (h + (k + 1) * x.charCodeAt(k)) % 1000000007; return h; });
  window.__srem.done = true;
})();
'started';
