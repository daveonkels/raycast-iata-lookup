function fold(value = "") {
  return value.normalize("NFKD").replace(/\p{M}/gu, "").trim().toLowerCase();
}

export function indexCatalog(rows) {
  return rows.map(row => ({
    row, code: fold(row.code), icao: fold(row.icao), name: fold(row.name), city: fold(row.city),
  })).sort((a, b) => a.code.localeCompare(b.code) || a.name.localeCompare(b.name));
}

function rankMatch({ code, icao, name, city }, q) {
  if (code === q || icao === q) return 0;
  if (name === q || city === q) return 1;
  if (code.startsWith(q)) return 2;
  if (q.length >= 2 && (name.startsWith(q) || city.startsWith(q))) return 3;
  if (q.length >= 3 && (name.includes(q) || city.includes(q))) return 4;
  return -1;
}

export function search(index, text) {
  const q = fold(text);
  if (!q) return [];
  const buckets = [[], [], [], [], []];
  for (const entry of index) {
    const rank = rankMatch(entry, q);
    if (rank >= 0 && buckets[rank].length < 3) buckets[rank].push(entry.row);
  }
  return buckets[0].length ? buckets[0] : buckets.flat().slice(0, 3);
}
