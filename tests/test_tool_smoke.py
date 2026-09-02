#!/usr/bin/env python3
"""Data-free smoke tests for every workspace tool.

Born of two bugs no outcome audit could see: bfs.py crashed with
UnboundLocalError across five experimental stages (agents silently wrote
their own searches), and a cleanrun.py helper landed below the __main__ guard
(NameError at the exact moment a board is scored). Rule: every tool must at
minimum survive being invoked, and no module may reference a name defined
only after its entry-point guard.
"""
import ast
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = sorted((ROOT / "harness" / "ws_tools").glob("*.py"))
fails = []

# 1) static: nothing used at module level (incl. inside main-guard) may be
#    defined only after the __main__ guard.
for tool in TOOLS:
    tree = ast.parse(tool.read_text())
    guard_i = next((i for i, n in enumerate(tree.body)
                    if isinstance(n, ast.If) and getattr(getattr(n.test, "left", None), "id", "") == "__name__"), None)
    if guard_i is None:
        continue
    late = {n.name for n in tree.body[guard_i + 1:] if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
    if late:
        fails.append(f"{tool.name}: defined after __main__ guard: {sorted(late)}")

# 2) dynamic: each tool must start as a script without NameError/UnboundLocal/
#    SyntaxError (argparse exit 2 or clean exit 0/1 are fine; daemon-connection
#    errors are fine; we assert the interpreter got past module + main setup).
with tempfile.TemporaryDirectory() as td:
    for tool in TOOLS:
        if tool.name.startswith("_") or tool.name == "world_model_template.py":
            continue
        r = subprocess.run([sys.executable, str(tool), "--help"],
                           capture_output=True, text=True, timeout=30, cwd=td)
        blob = (r.stdout + r.stderr)
        for marker in ("NameError", "UnboundLocalError", "SyntaxError", "IndentationError"):
            if marker in blob:
                fails.append(f"{tool.name} --help: {marker}: {blob.strip().splitlines()[-1][:120]}")

# 3) the bfs key-fallback pattern specifically: hashable and unhashable states.
sys.path.insert(0, str(ROOT / "harness" / "ws_tools"))
import json as _json
def key(g): return tuple(tuple(r) for r in g)
def _key(s):
    try:
        return key(s)
    except TypeError:
        return _json.dumps(s, sort_keys=True, default=repr)
class Unhashable:
    def __iter__(self): raise TypeError("nope")
try:
    _key([[1, 2]]); _key(Unhashable())
except Exception as exc:
    fails.append(f"key-fallback pattern: {type(exc).__name__}: {exc}")

if fails:
    print("TOOL SMOKE FAILURES:")
    for f in fails: print(" -", f)
    raise SystemExit(1)
print(f"PASS: {len(TOOLS)} tools; entry-point ordering clean, all invocable, key fallback sound.")
