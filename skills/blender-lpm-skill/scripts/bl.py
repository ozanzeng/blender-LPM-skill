#!/usr/bin/env python3
"""
bl.py - run Blender 5.2 headless from Claude Code on this workstation.

  python bl.py --script Pipeline/scan_assets.py -- --root Equipments
  python bl.py --blend GameReady/characters/archer.blend --expr "import bpy; print(bpy.data.objects.keys())"
  python bl.py --script inspect_scene.py -- --input Equipments/weapons/gladius.glb --out _work/i.json

Resolution order for the Blender executable: $BLENDER_EXE, the Blender 5.2 default install
path, then `blender` on PATH. Runs with --factory-startup unless --user-prefs is passed.
Everything the inner script prints is echoed; lines starting with '##JSON##' are also
collected and printed last as the machine-readable result. Exit code = Blender's exit code.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

DEFAULT_WINDOWS = r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
DEFAULT_MAC = "/Applications/Blender.app/Contents/MacOS/Blender"


def find_blender() -> str:
    env = os.environ.get("BLENDER_EXE")
    if env and Path(env).exists():
        return env
    for cand in (DEFAULT_WINDOWS, DEFAULT_MAC):
        if Path(cand).exists():
            return cand
    on_path = shutil.which("blender")
    if on_path:
        return on_path
    sys.exit("blender executable not found: set BLENDER_EXE or install Blender 5.2")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--blend", help=".blend file to open before running")
    p.add_argument("--script", help="python file to run inside Blender")
    p.add_argument("--expr", help="python expression/statements to run inside Blender")
    p.add_argument("--user-prefs", action="store_true", help="load user preferences/add-ons instead of factory settings")
    p.add_argument("--timeout", type=int, default=0, help="seconds; 0 = no limit")
    p.add_argument("script_args", nargs=argparse.REMAINDER, help="arguments after `--` are passed to the inner script")
    a = p.parse_args()
    if not a.script and not a.expr:
        p.error("give --script or --expr")

    cmd = [find_blender(), "--background", "--python-exit-code", "1"]   # script exceptions -> exit 1
    if not a.user_prefs:
        cmd.append("--factory-startup")
    if a.blend:
        cmd.append(str(Path(a.blend).resolve()))
    if a.script:
        cmd += ["--python", str(Path(a.script).resolve())]
    if a.expr:
        cmd += ["--python-expr", a.expr]
    rest = list(a.script_args)
    if rest and rest[0] == "--":
        rest = rest[1:]
    if rest:
        cmd += ["--", *rest]

    print("$ " + " ".join(f'"{c}"' if " " in c else c for c in cmd), flush=True)
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                encoding="utf-8", errors="replace", bufsize=1)
    except OSError as exc:
        sys.exit(f"failed to start Blender: {exc}")
    json_lines = []
    try:
        assert proc.stdout is not None
        for line in proc.stdout:
            sys.stdout.write(line)
            if line.startswith("##JSON##"):
                json_lines.append(line[len("##JSON##"):].strip())
        code = proc.wait(timeout=a.timeout or None)
    except subprocess.TimeoutExpired:
        proc.kill()
        print(f"!! timeout after {a.timeout}s, Blender killed", flush=True)
        return 124
    if json_lines:
        print("##RESULT## " + json_lines[-1], flush=True)
    return code


if __name__ == "__main__":
    sys.exit(main())
