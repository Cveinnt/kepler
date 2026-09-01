"""Render frames to PNG so you can LOOK at the game instead of reading cell text.

  python tools/render.py                  # current frame -> frames/current.png
  python tools/render.py --event 123      # that timeline event's settled frame
  python tools/render.py --event 123 --strip   # settled + any stored animation
                                               # frames side by side in one PNG

In visual mode the daemon also saves every frame of every action (including
animation frames) under frames/ as evNNNNN_fK.png — view those files directly.
Animation frames often show mechanisms that the settled grid hides.
"""
from __future__ import annotations

import argparse
import glob
import os

from _lib import WS, daemon, read_events
from _render_core import grid_to_png


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--event", type=int, default=None)
    ap.add_argument("--strip", action="store_true",
                    help="stitch the event's stored animation frames into one image")
    args = ap.parse_args()
    os.makedirs(WS / "frames", exist_ok=True)

    if args.event is None:
        st = daemon("/status")
        out = WS / "frames" / "current.png"
        grid_to_png(st["grid"], str(out))
        print(out)
        return

    evs = list(read_events())
    ev = next((e for e in evs if e.get("i") == args.event), None)
    if ev is None or not ev.get("grid"):
        raise SystemExit(f"no grid recorded for event {args.event}")
    out = WS / "frames" / f"ev{args.event:05d}.png"
    grid_to_png(ev["grid"], str(out))
    print(out)
    if args.strip:
        stored = sorted(glob.glob(str(WS / "frames" / f"ev{args.event:05d}_f*.png")))
        if stored:
            from PIL import Image
            imgs = [Image.open(p) for p in stored]
            strip = Image.new("RGB", (sum(i.width for i in imgs), imgs[0].height))
            x = 0
            for i in imgs:
                strip.paste(i, (x, 0)); x += i.width
            sp = WS / "frames" / f"ev{args.event:05d}_strip.png"
            strip.save(sp); print(sp)
        else:
            print("(no stored animation frames for this event — daemon was not "
                  "in visual mode when it was recorded)")


if __name__ == "__main__":
    main()
