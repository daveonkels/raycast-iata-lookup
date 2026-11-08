"""Build carrier and aircraft profiles from Duffel, OpenFlights and FAA inputs."""
import csv
import json
import re
import sys
from urllib.parse import urlsplit
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from openpyxl import load_workbook

root = Path(__file__).resolve().parents[1]
assets = Path(sys.argv[3]) if len(sys.argv) > 3 else root / "assets"
src = Path(sys.argv[1])
duffel_data = Path(sys.argv[2])

def records(file):
    with (src / file).open(encoding="utf-8", newline="") as stream:
        for row in csv.reader(stream):
            yield [None if v in ("", r"\N", "-") else v.strip() for v in row]

def key(name):
    return re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFKD", name or "").lower())

def model(name):
    name = (name or "").lower().replace("boeing (douglas)", "douglas").replace("mcdonnell douglas", "douglas")
    return key(name.replace("aerospatiale/alenia ", "").replace(" (bombardier)", ""))

def group(file, col):
    out = defaultdict(list)
    for row in records(file):
        if row[col]:
            out[row[col]].append(row)
    return out

def duffel(kind):
    return json.loads((duffel_data / f"{kind}.json").read_text())

def write(name, data):
    (assets / f"{name}.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":"), allow_nan=False))

carriers = group("airlines.dat", 3)
places = {row[0]: row for row in records("airports.dat")}
networks = defaultdict(set)
for carrier, ident, _, start, _, end, share, stops, _ in records("routes.dat"):
    if ident and not share and stops == "0" and start in places and end in places and start != end:
        networks[(ident, carrier)].add(tuple(sorted((start, end))))
airlines = {}
for row in duffel("airlines"):
    code = row['iata_code']
    if not code: continue
    candidates = [c for c in carriers[code] if key(row['name']) in (key(c[1]), key(c[2]))]
    url = urlsplit(row.get('conditions_of_carriage_url') or '')
    terms = url.hostname if url.scheme in ('https', 'http') else None
    if len(candidates) != 1:
        if terms: airlines[row['id']] = {'termsHost':terms}
        continue
    ident, name, alias, _, icao, call, country, _ = candidates[0]
    facts = {k:v for k,v in dict(termsHost=terms, directory=True, icao=icao if re.fullmatch('[A-Z]{3}',icao or '') else None,
              callsign=call, country=country, alias=alias if key(alias) != key(row['name']) else None).items() if v}
    routes = networks[(ident, code)]
    if routes:
        counts = Counter(station for pair in routes for station in pair)
        ranked = sorted(counts, key=lambda s:(-counts[s], places[s][1], s))
        facts['network'] = dict(pairs=len(routes), airports=len(counts),
            top=[dict(name=places[s][1], code=places[s][4], count=counts[s]) for s in ranked[:3]])
    if facts: airlines[row['id']] = facts
write('airline-profiles', airlines)

wb = load_workbook(src/'faa.xlsx', read_only=True, data_only=True)
rows = iter(wb['ACD_Data'].values)
headers = next(rows)
by_icao, by_model = defaultdict(list), defaultdict(list)
for values in rows:
    row = dict(zip(headers,values))
    if not row['ICAO_Code']: continue
    by_icao[row['ICAO_Code']].append(row)
    by_model[model(row['Model_FAA'])].append(row)
columns = dict(maker='Manufacturer',reference='Model_FAA',engine='Physical_Class_Engine',
    engines='Num_Engines',category='Class',wake='ICAO_WTC',length='Length_ft',
    span='Wingspan_ft_without_winglets_sharklets',spanTips='Wingspan_ft_with_winglets_sharklets',
    height='Tail_Height_at_OEW_ft',mtow='MTOW_lb',landing='MALW_lb',rotor='Rotor_Diameter_ft')
numeric = {'engines','length','span','spanTips','height','mtow','landing','rotor'}
planes = group('planes.dat',1)
aircraft = {}
fleet = duffel('aircraft')
# Only give related equipment a family when its catalogue name explicitly identifies that family.
family_re = re.compile(r'\b(Airbus A[23]\d{2}|Boeing [7]\d7|ATR [47]2|DHC-[68]|Embraer (?:170|175|190|195)|Saab (?:2000|340)|DC-\d+|MD-?\d{2}|Fokker (?:50|70|100)|Gulfstream G\d{3})', re.I)
for row in fleet:
    name,code=row['name'],row['iata_code']
    if not code: continue
    options=[p for p in planes[code] if model(p[0])==model(name) and p[2]]
    direct=by_model[model(name)]
    types={p[2] for p in options} | {r['ICAO_Code'] for r in direct}
    facts={}
    fam=family_re.search(name)
    if fam: facts['family']=fam[0]
    if len(types)==1:
        icao=types.pop()
        facts['icao']=icao
        profiles=direct or by_icao.get(icao,[])
        if len(profiles)==1:
            f=profiles[0]
            facts['faa']={k:f[v] for k,v in columns.items() if f[v] not in (None,'','N/A','Unknown','n/a','-')
                          and (k not in numeric or isinstance(f[v],(int,float)) and f[v]>0)}
    if facts: aircraft[row['id']]=facts
write('aircraft-profiles',aircraft)
print('airline directory',sum(r.get('directory',False) for r in airlines.values()),'archived networks',sum('network' in r for r in airlines.values()),
      'aircraft ICAO',sum('icao' in r for r in aircraft.values()),'FAA profiles',sum('faa' in r for r in aircraft.values()))
