#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from dut_topology import load_yaml, render_openwrt_host, render_openwrt_host_script


def main() -> None:
    ap = argparse.ArgumentParser(description="Render OpenWrt lab-owned network config fragment or UCI apply script.")
    ap.add_argument("--topology", required=True)
    ap.add_argument("--keys", required=True)
    ap.add_argument("--host", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--format", choices=["config", "script"], default="config")
    ap.add_argument("--allow-placeholder-keys", action="store_true")
    args = ap.parse_args()

    topo = load_yaml(args.topology)
    keys = load_yaml(args.keys) if Path(args.keys).exists() else {}
    if args.format == "script":
        rendered = render_openwrt_host_script(topo, args.host, keys, allow_placeholders=args.allow_placeholder_keys)
    else:
        rendered = render_openwrt_host(topo, args.host, keys, allow_placeholders=args.allow_placeholder_keys)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(rendered, encoding="utf-8")


if __name__ == "__main__":
    main()
