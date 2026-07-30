#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import uuid
from pathlib import Path
from typing import Any, Dict, List, Tuple

from dut_topology import fam_prefix4, load_yaml, one_vals, profile_device_id, two_vals, v4, v4_net


def stable_uuid(name: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"wg-dut-lab:{name}"))


def sanitize_filename(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", name).strip("-") + ".nmconnection"


def nm_keyfile(
    *,
    connection_id: str,
    interface_name: str,
    connection_type: str,
    addresses: List[str],
    routes: List[Tuple[str, str]],
    ipv6_addresses: List[str] | None = None,
    ipv6_routes: List[Tuple[str, str]] | None = None,
    mtu: int | None = None,
    vlan_parent: str | None = None,
    vlan_id: int | None = None,
) -> str:
    lines: List[str] = []
    lines += [
        "[connection]",
        f"id={connection_id}",
        f"uuid={stable_uuid(connection_id)}",
        f"type={connection_type}",
        f"interface-name={interface_name}",
        "autoconnect=true",
        "",
    ]
    if mtu is not None:
        lines += ["[ethernet]", f"mtu={mtu}", ""]
    else:
        lines += ["[ethernet]", ""]

    if connection_type == "vlan":
        if vlan_parent is None or vlan_id is None:
            raise ValueError("vlan_parent and vlan_id are required for VLAN profiles")
        lines += [
            "[vlan]",
            "flags=1",
            f"id={vlan_id}",
            f"parent={vlan_parent}",
            "",
        ]

    lines += ["[ipv4]"]
    for idx, address in enumerate(addresses, 1):
        lines.append(f"address{idx}={address}")
    lines += ["method=manual", "never-default=true"]
    for idx, (target, gateway) in enumerate(routes, 1):
        lines.append(f"route{idx}={target},{gateway}")
    lines.append("")

    ipv6_addresses = ipv6_addresses or []
    ipv6_routes = ipv6_routes or []
    lines += ["[ipv6]"]
    if ipv6_addresses:
        lines.append("addr-gen-mode=default")
        for idx, address in enumerate(ipv6_addresses, 1):
            lines.append(f"address{idx}={address}")
        lines += ["method=manual", "never-default=true"]
        for idx, (target, gateway) in enumerate(ipv6_routes, 1):
            lines.append(f"route{idx}={target},{gateway}")
    else:
        lines += ["addr-gen-mode=default", "method=link-local", "never-default=true"]
    lines += ["", "[proxy]", ""]
    return "\n".join(lines)


def render_two_dut_source_nm(topo: Dict[str, Any]) -> Tuple[str, str]:
    sh = topo.get("source_host", {})
    cfg = sh.get("two_dut", {})
    td = topo["two_dut"]
    addresses: List[str] = []
    routes: List[Tuple[str, str]] = []
    ipv6_addresses: List[str] = []
    ipv6_routes: List[Tuple[str, str]] = []

    for fam in td["families"]:
        for n in range(int(td["count"])):
            vals = two_vals(topo, fam, n)
            addresses.append(vals["source_plain4"])
            routes.append((vals["sink_plain_net4"], vals["enc_plain4"].split("/")[0]))
            if fam.get("include_ipv6") and "source_plain6" in vals:
                ipv6_addresses.append(vals["source_plain6"])
                if "sink_plain_net6" in vals:
                    ipv6_routes.append((vals["sink_plain_net6"], vals["enc_plain6"].split("/")[0]))

    name = cfg.get("connection_id", "D1-Supermicro")
    filename = cfg.get("filename", sanitize_filename(name))
    content = nm_keyfile(
        connection_id=name,
        interface_name=cfg.get("interface_name", "eth0"),
        connection_type=cfg.get("type", "ethernet"),
        addresses=addresses,
        routes=routes,
        ipv6_addresses=ipv6_addresses,
        ipv6_routes=ipv6_routes,
        mtu=cfg.get("mtu"),
    )
    return filename, content


def primary_source_host_address(topo: Dict[str, Any], family: Dict[str, Any], device_id: int) -> str:
    od = topo["one_dut"]
    d = od["defaults"]
    sh = topo.get("source_host", {}).get("one_dut", {})
    suffix = int(sh.get("source_host_primary_suffix", d.get("source_host_suffix", 1)))
    plen = int(sh.get("source_host_primary_prefixlen", d.get("source_net_prefixlen", 30)))
    return v4(fam_prefix4(topo, family, device_id), 1, suffix, plen)


def render_one_dut_source_nm(topo: Dict[str, Any], profile_name: str, profile: Dict[str, Any]) -> Tuple[str, str]:
    sh = topo.get("source_host", {}).get("one_dut", {})
    pcfg = sh.get("profiles", {}).get(profile_name, {})
    connection_id = pcfg.get("connection_id", profile.get("label", profile_name))
    filename = pcfg.get("filename", sanitize_filename(connection_id))
    vlan_id = int(pcfg.get("vlan_id", int(sh.get("vlan_id_base", 1200)) + int(profile_name.lstrip("d"))))

    addresses: List[str] = []
    routes: List[Tuple[str, str]] = []
    did = profile_device_id(profile)
    for fam in profile["families"]:
        addresses.append(primary_source_host_address(topo, fam, did))
        for n in range(int(profile["count"])):
            vals = one_vals(topo, profile, fam, n, did)
            addresses.append(vals["source_host_ip4"])
            routes.append((vals["tunnel_net4"], vals["dut_source_ip4"].split("/")[0]))

    content = nm_keyfile(
        connection_id=connection_id,
        interface_name=profile_name,
        connection_type=sh.get("type", "vlan"),
        addresses=addresses,
        routes=routes,
        vlan_parent=sh.get("parent", "eth1"),
        vlan_id=vlan_id,
    )
    return filename, content


def render_all(topo: Dict[str, Any]) -> Dict[str, str]:
    files: Dict[str, str] = {}
    filename, content = render_two_dut_source_nm(topo)
    files[filename] = content
    for profile_name, profile in topo["one_dut"]["profiles"].items():
        filename, content = render_one_dut_source_nm(topo, profile_name, profile)
        files[filename] = content
    return files


def main() -> None:
    ap = argparse.ArgumentParser(description="Render Arch NetworkManager source host keyfiles from topology.")
    ap.add_argument("--topology", required=True)
    ap.add_argument("--output-dir", required=True)
    args = ap.parse_args()
    topo = load_yaml(args.topology)
    outdir = Path(args.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    for filename, content in render_all(topo).items():
        (outdir / filename).write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
