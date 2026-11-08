"""Install validated data snapshots from the public main branch on this Mac."""
import argparse
import ctypes
import fcntl
import hashlib
import io
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile

HOME = Path.home()
STATE = HOME / "Library/Application Support/IATA Lookup Updater"
INSTALLED = HOME / ".config/raycast/extensions/iata-offline"
REMOTE = "https://github.com/daveonkels/raycast-iata-lookup.git"
CACHE = STATE / "data.git"
DATA_FILES = ("catalog.json", "sources.json", "airline-profiles.json", "aircraft-profiles.json")
MARKER = ".iata-data-version.json"


def run(args, **kwargs):
    return subprocess.run(args, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          timeout=150, **kwargs).stdout


def git(directory, *args):
    return run(["/usr/bin/git", "-C", directory, "-c", "credential.helper=", *args])


def data_digest(assets):
    digest = hashlib.sha256()
    for relative in sorted([Path(f) for f in DATA_FILES] + [p.relative_to(assets) for p in (assets / "airfields").glob("*.json")]):
        digest.update(str(relative).encode() + b"\0" + hashlib.sha256((assets / relative).read_bytes()).digest())
    return digest.hexdigest()


def prepare(source, revision, checkout):
    # Only locally approved code may execute. Remote inputs are regular JSON files.
    archive = git(checkout, "archive", "refs/heads/main", "package.json", "src", "assets", "tools")
    run(["/usr/bin/tar", "-xf", "-", "-C", source], input=archive)
    assets = source / "assets"
    shutil.rmtree(assets / "airfields")
    (assets / "airfields").mkdir()
    paths = ["assets/" + f for f in DATA_FILES] + ["assets/airfields"]
    remote = git(CACHE, "archive", revision, "--", *paths)
    copied = set()
    with tarfile.open(fileobj=io.BytesIO(remote)) as archive:
        for member in archive:
            if member.isdir():
                continue
            if not member.isfile() or not (member.name in paths[:-1] or re.fullmatch(r"assets/airfields/[A-Z0-9]\.json", member.name)):
                raise ValueError(f"Unexpected snapshot file {member.name!r}")
            with archive.extractfile(member) as incoming, (source / member.name).open("wb") as dest:
                shutil.copyfileobj(incoming, dest)
            copied.add(member.name)
    if not set(paths[:-1]) <= copied:
        raise ValueError("Incomplete data snapshot")


def update(checkout, ray):
    if not CACHE.is_dir():
        run(["/usr/bin/git", "init", "--bare", CACHE])
    git(CACHE, "fetch", "--quiet", "--no-tags", "--depth=1", REMOTE, "refs/heads/main")
    revision = git(CACHE, "rev-parse", "FETCH_HEAD").decode().strip()
    tree = git(CACHE, "rev-parse", revision + ":assets").decode().strip()
    marker = INSTALLED / MARKER
    if marker.exists():
        last = json.loads(marker.read_text())
        if last["tree"] == tree and data_digest(INSTALLED / "assets") == last["digest"]:
            return
    if INSTALLED.is_symlink() or json.loads((INSTALLED / "package.json").read_text())["name"] != "iata-offline":
        raise ValueError("Expected the existing iata-offline installation")

    with tempfile.TemporaryDirectory(dir=STATE) as temp:
        source = Path(temp) / "source"
        bundle = Path(temp) / "bundle"
        source.mkdir()
        prepare(source, revision, checkout)
        run([ray, "build", "--exit-on-error", "-e", "dev", "-o", bundle], cwd=source)
        assets = bundle / "assets"
        run([sys.executable, source / "tools/snapshot.py", assets])
        run(["node", source / "tools/check-search.mjs", assets])
        digest = data_digest(assets)
        if digest != data_digest(source / "assets") or not (bundle / "search.js").stat().st_size:
            raise ValueError("Raycast build failed snapshot verification")
        for filename in ("cli.pid", "dev.log"):
            if (INSTALLED / filename).is_file():
                shutil.copy2(INSTALLED / filename, bundle / filename)
        (bundle / MARKER).write_text(json.dumps(dict(commit=revision, tree=tree, digest=digest)) + "\n")
        # Darwin RENAME_SWAP replaces the whole live bundle atomically on the same volume.
        rename = ctypes.CDLL(None, use_errno=True).renamex_np
        rename.argtypes = (ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint)
        if rename(os.fsencode(bundle), os.fsencode(INSTALLED), 2) != 0:
            err = ctypes.get_errno()
            raise OSError(err, os.strerror(err))
    logging.info("Installed main %s", revision)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", required=True, type=Path)
    parser.add_argument("--ray", required=True, type=Path)
    args = parser.parse_args()
    os.umask(0o077)
    os.environ["GIT_TERMINAL_PROMPT"] = "0"
    STATE.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        handlers=[RotatingFileHandler(STATE / "updater.log", maxBytes=128000, backupCount=2)])
    with (STATE / "run.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            sys.exit(0)
        try:
            update(args.checkout, args.ray)
        except subprocess.CalledProcessError as exc:
            logging.error("%s: %s", Path(str(exc.cmd[0])).name, (exc.stderr or exc.stdout).decode(errors="replace")[-2500:])
            sys.exit(1)
        except Exception:
            logging.exception("Snapshot update failed")
            sys.exit(1)
