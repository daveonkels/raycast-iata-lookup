"""Build offline assets from OurAirports revision bdbcf5e2643119210d5c240f2e26ab2604ec5e38 (2026-11-07)."""
import csv
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

source = Path(sys.argv[1])
duffel_data = Path(sys.argv[2])
root = Path(__file__).resolve().parents[1]
assets = root / 'assets/airfields'
assets.mkdir(exist_ok=True)


def rows(table):
    with (source / (table + '.csv')).open(encoding='utf-8-sig', newline='') as stream:
        yield from csv.DictReader(stream)


def fields(row, keys):
    return {key: row[key] for key in keys.split() if row[key] != ''}


regions = {r['code']: r['name'] for r in rows('regions')}
by_icao, by_iata = defaultdict(list), defaultdict(list)
for r in rows('airports'):
    for code in {r['icao_code'], r['ident']} - {''}:
        by_icao[(r['iso_country'], code)].append(r)
    if r['iata_code']:
        by_iata[(r['iso_country'], r['iata_code'])].append(r)

runways, radios, navaids = defaultdict(list), defaultdict(list), defaultdict(list)
for r in rows('runways'):
    ends = ' '.join(f'{end}_{field}' for end in ('le', 'he') for field in
                    ('ident', 'latitude_deg', 'longitude_deg', 'elevation_ft', 'heading_degT', 'displaced_threshold_ft'))
    runways[r['airport_ref']].append(fields(r, 'length_ft width_ft surface lighted closed ' + ends))
for r in rows('airport-frequencies'):
    radios[r['airport_ref']].append(fields(r, 'type description frequency_mhz'))
for r in rows('navaids'):
    if r['associated_airport']:
        navaids[(r['iso_country'], r['associated_airport'])].append(fields(r, 'name type ident frequency_khz dme_channel'))

shards = defaultdict(dict)
matched = 0
for airport in json.loads((duffel_data / 'airports.json').read_text()):
    country, iata, icao = (airport[k] for k in ('iata_country_code', 'iata_code', 'icao_code'))
    lat, lon = airport['latitude'], airport['longitude']
    detail = {'lat': lat, 'lon': lon}
    candidates = by_icao.get((country, icao), []) or by_iata.get((country, iata), [])
    # Reject distant reassignments, conflicting codes, and ambiguous matches.
    nearby = []
    for field in candidates:
        if field['iata_code'] and field['iata_code'] != iata:
            continue
        if icao and field['icao_code'] and field['icao_code'] != icao:
            continue
        dy = math.radians(float(field['latitude_deg']) - lat)
        dx = math.radians(float(field['longitude_deg']) - lon)
        h = math.sin(dy / 2)**2 + math.cos(math.radians(lat)) * math.cos(math.radians(float(field['latitude_deg']))) * math.sin(dx / 2)**2
        if 12742 * math.asin(math.sqrt(min(1, h))) <= 25:
            nearby.append(field)
    if len(nearby) == 1:
        r = nearby[0]
        matched += 1
        detail.update(fields(r, 'type elevation_ft scheduled_service local_code'))
        detail.update(region=regions.get(r['iso_region']), runways=runways[r['id']],
                      radios=radios[r['id']], navaids=navaids[(country, r['ident'])],
                      lat=float(r['latitude_deg']), lon=float(r['longitude_deg']))
    shards[iata[0]][airport['id']] = detail
for initial, data in shards.items():
    assert initial.isascii() and initial.isalnum()
    (assets / (initial + '.json')).write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')))
print(f'{matched} enriched airports out of {sum(map(len, shards.values()))}')
