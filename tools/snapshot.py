"""Validate a bundled snapshot and describe changes by aviation identifier."""
import argparse
import json
import math
import re
from collections import defaultdict
from pathlib import Path


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition, message):
    if not condition:
        raise ValueError(message)


class Snapshot:
    def __init__(self, assets):
        self.rows = {}
        self.codes = defaultdict(set)
        for row in read(assets / "catalog.json"):
            kind, ident, code = row["kind"], row["id"], row["code"]
            require(kind in {"Airport", "Airline", "Aircraft"}, f"Unknown catalog kind {kind!r}")
            require(all(isinstance(row[k], str) and row[k].strip() for k in ("id", "name", "code")),
                    f"Missing identity for {ident!r}")
            require(ident not in self.rows, f"Duplicate record {ident!r}")
            self.rows[ident] = row
            self.codes[kind, code].add(ident)

        self.fields = {}
        for shard in sorted((assets / "airfields").glob("*.json")):
            for ident, field in read(shard).items():
                row = self.rows.get(ident, {})
                require(row.get("kind") == "Airport" and row["code"][0] == shard.stem,
                        f"Misplaced airport {ident} in {shard.name}")
                for axis, bound in (("lat", 90), ("lon", 180)):
                    n = field.get(axis)
                    require(type(n) in (int, float) and math.isfinite(n) and abs(n) <= bound,
                            f"Invalid {axis} for {ident}")
                self.fields[ident] = field
        self.carriers = read(assets / "airline-profiles.json")
        self.planes = read(assets / "aircraft-profiles.json")
        for kind, records in (("Airport", self.fields), ("Airline", self.carriers), ("Aircraft", self.planes)):
            ids = {ident for ident, row in self.rows.items() if row["kind"] == kind}
            require(records and set(records) <= ids, f"Empty or orphaned {kind} detail records")
            if kind == "Airport":
                require(ids == set(records), "Missing airport detail records")
        require(any(f.get("runways") for f in self.fields.values()), "Entire runway dataset missing")
        require(any(f.get("radios") for f in self.fields.values()), "Entire frequency dataset missing")
        require(any(f.get("network") for f in self.carriers.values()), "Entire route archive missing")
        require(any(f.get("faa", {}).get("length") for f in self.planes.values()), "Entire FAA dataset missing")


def report(before, after):
    lines = ["## Snapshot review", "", "| Change | Count | Example codes (up to 12) |",
             "| --- | ---: | --- |"]

    def count(label, codes):
        codes = sorted(codes)
        # Data is displayed in public PRs. Limit examples to plain aviation codes.
        examples = [code for code in codes if re.fullmatch(r"[A-Za-z0-9]{1,5}", code)]
        sample = ", ".join(examples[:12])
        lines.append(f"| {label} | {len(codes):,} | {sample or '—'} |")

    for kind in ("Airport", "Airline", "Aircraft"):
        old = {key for key, row in before.rows.items() if row["kind"] == kind}
        new = {key for key, row in after.rows.items() if row["kind"] == kind}
        count(f"{kind} records added", (after.rows[k]["code"] for k in new - old))
        count(f"{kind} records removed", (before.rows[k]["code"] for k in old - new))
    count("Codes with changed assignments", (code for kind, code in before.codes.keys() & after.codes.keys()
                                             if before.codes[kind, code] != after.codes[kind, code]))
    count("Catalog entries edited", (after.rows[k]["code"] for k in before.rows.keys() & after.rows.keys()
                                     if before.rows[k] != after.rows[k]))
    shared = before.fields.keys() & after.fields.keys()
    count("Airfield locations or elevations changed", (after.rows[k]["code"] for k in shared
          if any(before.fields[k].get(f) != after.fields[k].get(f) for f in ("lat", "lon", "elevation_ft"))))
    for label, field in (("Runways", "runways"), ("Frequencies", "radios"), ("Navaids", "navaids")):
        count(f"{label} changed", (after.rows[k]["code"] for k in shared
                                   if before.fields[k].get(field, []) != after.fields[k].get(field, [])))
    for label, previous, candidate, key in (
        ("Airfields", before.fields, after.fields, "type"), ("Carrier identifications", before.carriers, after.carriers, "directory"),
        ("Archived networks", before.carriers, after.carriers, "network"), ("Aircraft specifications", before.planes, after.planes, "faa")
    ):
        count(f"{label} lost", (before.rows[k]["code"] for k, v in previous.items()
                                if v.get(key) and not candidate.get(k, {}).get(key)))
    count("Aircraft specifications changed", (after.rows[k]["code"] for k in before.planes.keys() & after.planes.keys()
                                              if before.planes[k].get("faa") != after.planes[k].get("faa")))
    count("Carrier identifications changed", (after.rows[k]["code"] for k in before.carriers.keys() & after.carriers.keys()
                                              if any(before.carriers[k].get(f) != after.carriers[k].get(f)
                                                     for f in ("icao", "callsign", "country"))))
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("assets", type=Path)
    parser.add_argument("--against", type=Path)
    args = parser.parse_args()
    current = Snapshot(args.assets)
    print(report(Snapshot(args.against), current) if args.against else f"Validated {len(current.rows):,} records")
