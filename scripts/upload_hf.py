#!/usr/bin/env python3
"""Upload the traces/ dataset (built by export_traces.py) to a HuggingFace dataset repo.

Prepared ahead of HF auth being available, this script is NOT run as part of
the repo build. It needs:
  - `pip install huggingface_hub`
  - an HF token with write access in the HF_TOKEN environment variable
  - traces/ already built
    (python3 scripts/export_traces.py --release --with-agent-logs)

Usage:
  HF_TOKEN=hf_... python3 scripts/upload_hf.py --repo <user>/<dataset-name>
  HF_TOKEN=hf_... python3 scripts/upload_hf.py --repo <user>/<dataset-name> \
      --traces-dir traces --private --message "add opus traces"
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True,
                    help="dataset repo id, e.g. someuser/kepler-arcagi3-traces")
    ap.add_argument("--traces-dir", default=str(ROOT / "traces"))
    ap.add_argument("--private", action="store_true",
                    help="create the dataset repo as private")
    ap.add_argument("--message", default="upload ARC-AGI-3 agent harness traces")
    args = ap.parse_args()

    token = os.environ.get("HF_TOKEN")
    if not token:
        sys.exit("HF_TOKEN not set, export a write token first "
                 "(https://huggingface.co/settings/tokens)")

    traces = Path(args.traces_dir)
    if not (traces / "runs.jsonl").exists() or not (traces / "README.md").exists():
        sys.exit(f"{traces} does not look like an export "
                 f"(runs.jsonl / README.md missing), run scripts/export_traces.py first")

    try:
        from huggingface_hub import HfApi
    except ImportError:
        sys.exit("huggingface_hub not installed, pip install huggingface_hub")

    api = HfApi(token=token)
    api.create_repo(args.repo, repo_type="dataset", private=args.private, exist_ok=True)
    info = api.upload_folder(
        folder_path=str(traces),
        repo_id=args.repo,
        repo_type="dataset",
        commit_message=args.message,
    )
    print(f"uploaded {traces} -> https://huggingface.co/datasets/{args.repo}")
    print(f"commit: {getattr(info, 'oid', info)}")


if __name__ == "__main__":
    main()
