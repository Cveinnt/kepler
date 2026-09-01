#!/usr/bin/env python3
"""Launch a harness run fully detached from the calling process tree.

Long runs kept dying when started as a child of a supervised shell session: the
supervisor reaps its process group on exit and takes the run with it, mid-game.
macOS has no setsid(1), so this does the classic double-fork: the run ends up in
its own session, owned by init, and survives whatever happens to the launcher.

Nothing is lost when a run is killed anyway — no result.json is written, and the
workspace keeps the world model, notes and append-only ledger — but a run that
cannot survive its own launcher can never finish, either.

Usage:
  python3 scripts/detach_run.py --log /tmp/run.log -- \
      .venv/bin/python harness/run_game.py --game sp80 --model opus --resume
"""

from __future__ import annotations

import argparse
import os
import sys


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", required=True, help="file to receive stdout+stderr")
    ap.add_argument("cmd", nargs=argparse.REMAINDER,
                    help="-- followed by the command to run")
    args = ap.parse_args()
    cmd = args.cmd[1:] if args.cmd and args.cmd[0] == "--" else args.cmd
    if not cmd:
        raise SystemExit("no command given (put it after --)")

    # First fork: parent returns to the caller immediately.
    if os.fork() > 0:
        return 0
    os.setsid()                      # new session; no controlling terminal
    # Second fork: guarantees the runner can never reacquire a terminal.
    if os.fork() > 0:
        os._exit(0)

    log = open(args.log, "ab", buffering=0)
    os.dup2(os.open(os.devnull, os.O_RDONLY), 0)
    os.dup2(log.fileno(), 1)
    os.dup2(log.fileno(), 2)
    os.chdir(os.path.dirname(os.path.abspath(__file__)) + "/..")
    os.execvp(cmd[0], cmd)           # replace this process with the run
    os._exit(127)                    # only reached if exec failed


if __name__ == "__main__":
    sys.exit(main())
