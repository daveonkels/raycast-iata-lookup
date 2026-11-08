"""Build the search index from a local copy of the Duffel snapshot."""
import json
import sys
from pathlib import Path

source = Path(sys.argv[1])
assets = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).resolve().parents[1] / "assets"
catalog = []
airport_fields = {"icao": "icao_code", "city": "city_name", "country": "iata_country_code", "zone": "time_zone"}
for kind, filename in [("Airport", "airports"), ("Airline", "airlines"), ("Aircraft", "aircraft")]:
    for row in json.loads((source / f"{filename}.json").read_text(encoding="utf-8")):
        if not row["iata_code"]:
            continue
        entry = dict(kind=kind, code=row["iata_code"], name=row["name"], id=row["id"])
        if kind == "Airport":
            entry.update({label: row[key] for label, key in airport_fields.items() if row[key]})
        catalog.append(entry)

(assets / "catalog.json").write_text(json.dumps(catalog, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
