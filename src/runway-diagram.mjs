// Project surveyed endpoints onto a local east/north plane. Each axis uses the same scale.
export function diagram(runways, latitude, longitude) {
  const project = (lat, lon) => [
    (((Number(lon) - longitude + 540) % 360) - 180) * Math.cos(latitude * Math.PI / 180),
    latitude - Number(lat),
  ];
  const strips = runways.filter(r =>
    ["le_latitude_deg", "le_longitude_deg", "he_latitude_deg", "he_longitude_deg"]
      .every(k => r[k] != null && Number.isFinite(Number(r[k])) && Math.abs(Number(r[k])) <= (k.includes("latitude") ? 90 : 180))
  ).map(r => ({ r, a: project(r.le_latitude_deg, r.le_longitude_deg),
    b: project(r.he_latitude_deg, r.he_longitude_deg) }))
    .filter(({a,b}) => Math.hypot(a[0]-b[0],a[1]-b[1]) > 0.00001);
  if (!strips.length) return "";
  const points = strips.flatMap(s => [s.a, s.b]);
  const xs = points.map(p => p[0]), ys = points.map(p => p[1]);
  const left = Math.min(...xs), right = Math.max(...xs), top = Math.min(...ys), bottom = Math.max(...ys);
  const scale = Math.min(420 / (right - left), 150 / (bottom - top));
  const xy = p => [260 + (p[0] - (right + left) / 2) * scale, 112 + (p[1] - (top + bottom) / 2) * scale];
  const lines = [], labels = [];
  for (const {r, a, b} of strips) {
    const [x,y] = xy(a), [u,v] = xy(b);
    const segment = 'x1="'+x+'" y1="'+y+'" x2="'+u+'" y2="'+v+'"';
    const closed = r.closed === "1";
    lines.push('<line '+segment+' stroke="'+(closed ? "#9a8880" : "#a7d4eb")+'" stroke-width="6"/><line '+segment+' stroke="#1b3345" stroke-width="1" stroke-dasharray="5 4"/>');
    const length = Math.hypot(u-x,v-y);
    for (const [px,py,dir,id] of [[x,y,-1,r.le_ident],[u,v,1,r.he_ident]]) {
      if (!id || !/^[0-9A-Za-z-]{1,7}$/.test(id)) continue;
      const lx = px + dir * (u-x) / length * 18, ly = py + dir * (v-y) / length * 15 + 4;
      labels.push('<text x="'+lx+'" y="'+ly+'" text-anchor="middle" fill="#edf6fb" stroke="#152635" stroke-width="3" paint-order="stroke">'+id+'</text>');
    }
  }
  const svg = '<svg xmlns="http://www.w3.org/2000/svg" width="520" height="224" viewBox="0 0 520 224"><rect width="520" height="224" rx="12" fill="#152635"/><g font-family="monospace" font-size="13"><text x="16" y="22" fill="#a7d4eb">RUNWAY LAYOUT</text><path d="M493 46v-18m-5 7 5-8 5 8" fill="none" stroke="#a7d4eb" stroke-width="2"/><text x="489" y="20" fill="#a7d4eb">N</text>'+lines.join("")+labels.join("")+'</g></svg>';
  return 'data:image/svg+xml;base64,' + Buffer.from(svg).toString("base64");
}
