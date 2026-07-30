#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from dut_topology import load_yaml, render_arch_source


def main() -> None:
    ap = argparse.ArgumentParser(description="Render Arch systemd-networkd source host config.")
    ap.add_argument("--topology", required=True)
    ap.add_argument("--interface", default="eth0")
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    topo = load_yaml(args.topology)
    rendered = render_arch_source(topo, args.interface)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(rendered, encoding="utf-8")


if __name__ == "__main__":
    main()
