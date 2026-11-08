"""Set up the daily IATA Lookup data updater for the current macOS user."""
import argparse
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys
import tempfile

LABEL = "com.daveonkels.raycast-iata-update"
CHECKOUT = Path(__file__).resolve().parents[2]
PLIST = Path.home() / "Library/LaunchAgents" / (LABEL + ".plist")
STATE = Path.home() / "Library/Application Support/IATA Lookup Updater"
PROGRAM = STATE / "update.py"
DOMAIN = f"gui/{os.getuid()}"


def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as out:
        try:
            out.write(data)
            out.flush()
            os.replace(out.name, path)
        finally:
            Path(out.name).unlink(missing_ok=True)


def unload():
    target = DOMAIN + "/" + LABEL
    loaded = subprocess.run(["/bin/launchctl", "print", target], capture_output=True)
    if loaded.returncode == 0:
        subprocess.run(["/bin/launchctl", "bootout", target], check=True)
        return True
    return False


def install(ray_path):
    installed = Path.home() / ".config/raycast/extensions/iata-offline/package.json"
    if not installed.is_file() or json.loads(installed.read_text()).get("name") != "iata-offline":
        raise SystemExit("Install Search IATA Codes with ray develop first.")
    ray = shutil.which(os.path.abspath(os.path.expanduser(ray_path)) if "/" in ray_path else ray_path)
    if not ray:
        raise SystemExit("Cannot find the Raycast CLI. Pass --ray /path/to/node_modules/.bin/ray.")
    if not shutil.which("node"):
        raise SystemExit("Run setup from a shell with Node.js 22.14 or newer.")
    # Version managers often put temporary shell-specific symlinks on PATH.
    node = Path(subprocess.check_output(["node", "-p", "process.execPath"], text=True).strip()).resolve()
    subprocess.run(["/usr/bin/git", "-C", CHECKOUT, "rev-parse", "--verify", "--quiet", "refs/heads/main"],
                   check=True, stdout=subprocess.DEVNULL)
    job = dict(Label=LABEL, ProcessType="Background", StartCalendarInterval=dict(Hour=9, Minute=0),
               ProgramArguments=[sys.executable, str(PROGRAM), "--checkout", str(CHECKOUT),
                                 "--ray", os.path.abspath(ray)],
               EnvironmentVariables={"PATH": f"{node.parent}:/usr/bin:/bin:/usr/sbin:/sbin"})
    files = {PROGRAM: Path(__file__).with_name("update.py").read_bytes(), PLIST: plistlib.dumps(job)}
    previous = {path: path.read_bytes() if path.exists() else None for path in files}
    loaded = unload()
    try:
        for path, contents in files.items():
            atomic_write(path, contents)
        subprocess.run(["/bin/launchctl", "bootstrap", DOMAIN, PLIST], check=True)
    except (OSError, subprocess.CalledProcessError):
        for path, contents in previous.items():
            if contents is None:
                path.unlink(missing_ok=True)
            else:
                atomic_write(path, contents)
        if loaded:
            subprocess.run(["/bin/launchctl", "bootstrap", DOMAIN, PLIST], check=True)
        raise
    print("Daily update scheduled for 9:00 AM local time.")


def uninstall():
    unload()
    PLIST.unlink(missing_ok=True)
    PROGRAM.unlink(missing_ok=True)
    print("Removed the daily updater. Your installed extension, data cache and logs are retained.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ray", default="ray", help="path to the installed Raycast CLI")
    parser.add_argument("--uninstall", action="store_true", help="remove the daily job")
    args = parser.parse_args()
    if sys.platform != "darwin":
        parser.error("This updater uses macOS launchd.")
    if args.uninstall:
        uninstall()
    else:
        install(args.ray)
