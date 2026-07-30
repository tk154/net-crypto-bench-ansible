#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from dut_topology import generate_keys, load_yaml


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate WireGuard/WolfGuard tunnel keys from compact topology data.")
    ap.add_argument("--topology", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--skip-wolfguard", action="store_true")
    ap.add_argument("--allow-dummy", action="store_true", help="Only for renderer testing; never deploy dummy keys.")
    args = ap.parse_args()
    topo = load_yaml(args.topology)
    generate_keys(topo, Path(args.output), force=args.force, skip_wolfguard=args.skip_wolfguard, allow_dummy=args.allow_dummy)


if __name__ == "__main__":
    main()
