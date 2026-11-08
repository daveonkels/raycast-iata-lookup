"""Build and verify a candidate snapshot in a new directory."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from hashlib import sha256
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
from urllib.parse import urljoin, urlsplit

from snapshot import Snapshot, read, report, require

ROOT = Path(__file__).resolve().parents[1]
FAA_PAGE = "https://www.faa.gov/airports/engineering/aircraft_char_database"
# Fixed file lists keep upstream data out of executable paths.
SOURCES = {
    "duffel": ("timrogers/iata-code-decoder-api", "data/", ("airports.json", "airlines.json", "aircraft.json")),
    "ourairports": ("davidmegginson/ourairports-data", "", ("airports.csv", "regions.csv", "runways.csv", "airport-frequencies.csv", "navaids.csv")),
    "openflights": ("jpatokal/openflights", "data/", ("airports.dat", "airlines.dat", "planes.dat", "routes.dat")),
}


def fetch(url, output=None):
    command = ["curl", "--fail", "--silent", "--show-error", "--location", "--proto", "=https",
               "--proto-redir", "=https", "--retry", "2", "--max-time", "60", "--max-filesize", "80000000"]
    if output:
        subprocess.run([*command, "--output", output, url], check=True)
    else:
        return subprocess.check_output([*command, url])


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def get_source(name, previous, directory, locked):
    repo, prefix, files = SOURCES[name]
    directory.mkdir()
    rev, stamp = previous["revision"], previous["date"]
    if not locked:
        query = "?per_page=1" + ("&path=data" if prefix else "")
        head = json.loads(fetch(f"https://api.github.com/repos/{repo}/commits{query}"))[0]
        rev = head["sha"]
        stamp = date.fromisoformat(head["commit"]["committer"]["date"][:10]).isoformat()
    require(re.fullmatch("[0-9a-f]{40}", rev), f"Invalid revision for {name}")
    for file in files:
        fetch(f"https://raw.githubusercontent.com/{repo}/{rev}/{prefix}{file}", directory / file)
    hashes = {file: digest(directory / file) for file in sorted(files)}
    if hashes == previous["files"]:
        return previous
    require(not locked, f"Inputs differ from their recorded hashes for {name}")
    if name == "openflights":
        require(hashes["routes.dat"] == previous["files"]["routes.dat"],
                "OpenFlights routes.dat changed. Confirm its archive edition before updating the route pin.")
    return {**previous, "revision": rev, "date": stamp, "files": hashes}


class WorkbookLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.href = None
        self.parts = []
        self.matches = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.href = dict(attrs).get("href")
            self.parts = []

    def handle_data(self, data):
        if self.href:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if tag != "a" or not self.href:
            return
        label = " ".join("".join(self.parts).split())
        match = re.fullmatch(r"Aircraft Characteristics\s*\(([A-Za-z]+ [0-9]{4})\)", label, re.I)
        if match:
            edition = datetime.strptime(match[1], "%B %Y")
            url = urljoin(FAA_PAGE, self.href)
            require(urlsplit(url).netloc == "www.faa.gov" and urlsplit(url).scheme == "https", "Unexpected FAA workbook host")
            self.matches.append((edition, url))
        self.href = None


def get_faa(previous, path, locked):
    if locked:
        shutil.copyfile(ROOT / "data/faa.xlsx", path)
        require(digest(path) == previous["sha256"], "FAA workbook differs from recorded checksum")
        return previous
    links = WorkbookLinks()
    links.feed(fetch(FAA_PAGE).decode("utf-8"))
    require(links.matches, "FAA edition could not be identified. Inspect the official publication page.")
    edition, url = max(links.matches)
    require(edition >= datetime.strptime(previous["edition"], "%B %Y"), "FAA edition moved backwards")
    fetch(url, path)
    return {"url": url, "edition": edition.strftime("%B %Y"), "sha256": digest(path)}


def build(work, locked):
    previous = read(ROOT / "assets/sources.json")
    refs = {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        jobs = {k: pool.submit(get_source, k, previous[k], work/k, locked) for k in SOURCES}
        faa = pool.submit(get_faa, previous["faa"], work/"faa.xlsx", locked)
        for name, job in jobs.items():
            refs[name] = job.result()
        refs["faa"] = faa.result()

    candidate = work / "candidate"
    assets = candidate / "assets"
    assets.mkdir(parents=True)
    shutil.copyfile(work/"faa.xlsx", work/"openflights/faa.xlsx")
    for tool, dirs in (("catalog", ["duffel"]), ("airfields", ["ourairports", "duffel"]),
                       ("profiles", ["openflights", "duffel"])):
        subprocess.run([sys.executable, ROOT/f"tools/prepare-{tool}.py", *(work/d for d in dirs), assets], check=True)
    (assets / "sources.json").write_text(json.dumps(refs, indent=2) + "\n")
    (candidate / "data").mkdir()
    shutil.copyfile(work/"faa.xlsx", candidate/"data/faa.xlsx")
    review = report(Snapshot(ROOT/"assets"), Snapshot(assets))
    subprocess.run(["node", ROOT/"tools/check-search.mjs", assets], check=True)
    source_lines = ["## Source revisions", ""]
    for key in SOURCES:
        source_lines.append(f"- {key}: {previous[key]['revision'][:12]} → {refs[key]['revision'][:12]} ({refs[key]['date']})")
    source_lines.append(f"- FAA: {refs['faa']['edition']}, workbook SHA-256 {refs['faa']['sha256'][:16]}")
    (candidate/"review.md").write_text("\n".join(source_lines) + "\n\n" + review)
    return candidate


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="New directory for validated assets, workbook and review report")
    parser.add_argument("--locked", action="store_true", help="Reproduce the committed source revisions and hashes")
    args = parser.parse_args()
    require(not args.output.exists(), "Choose a fresh output directory")
    with TemporaryDirectory(dir=args.output.parent) as temp:
        candidate = build(Path(temp), args.locked)
        candidate.rename(args.output)
    print((args.output/"review.md").read_text())
