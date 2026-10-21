# Network Encryption Benchmark Automation

Ansible automation for benchmarking plaintext, WireGuard, WolfGuard, and MACsec
on OpenWrt, including eBPF/XDP and eBPF/TC acceleration.

The suite defines lab topologies, manages cryptographic keys, and generates
configurations for an Arch Linux traffic source, OpenWrt devices under test
(DuTs), and an OpenWrt traffic sink.
<br><br>

## Architecture and Topologies

The lab environment supports two primary network topologies. Both support
plaintext, WireGuard, WolfGuard, and MACsec traffic.
The traffic source, traffic sink, and the dedicated encryptor/decryptor devices in the Two-DuT setup are all powered by identical Supermicro servers with the following specifications:

| Component | Model / Type |
| --- | --- |
| **Mainboard** | Supermicro H13SSL-NT |
| **CPU** | 16-core AMD EPYC 9124 |
| **NIC** | 100G Mellanox ConnectX-6 Dx |
<br>

### 1. Two-DuT Setup (`two_dut`)

A two DuT / four-device setup designed to test dedicated encryptor and decryptor devices between a traffic source and sink.

```text
+-------------------------+             +------------------------+             +------------------------+             +-------------------------+
|     Traffic Source      |             |     Encryptor DuT      |             |     Decryptor DuT      |             |      Traffic Sink       |
| Supermicro / Arch Linux |  Plaintext  |  Supermicro / OpenWrt  |  Test link  |  Supermicro / OpenWrt  |  Plaintext  |  Supermicro / OpenWrt   |
|       10.201.99.1       | ----------> |      10.201.99.2       | ----------> |      10.201.99.3       | ----------> |       10.201.99.4       |
+-------------------------+             +------------------------+             +------------------------+             +-------------------------+
```

### 2. One-DuT Setup (`one_dut`)

A one DuT / three-device setup where a single Device under Test (DuT) routes
plaintext traffic or encrypts and decrypts traffic between the source and sink.

```text
+-------------------------+             +---------------------------+             +-------------------------+
|     Traffic Source      |             | Encryptor / Decryptor DuT |             |      Traffic Sink       |
| Supermicro / Arch Linux |  Plaintext  |        dX / OpenWrt       |  Test link  |  Supermicro / OpenWrt   |
|       10.201.99.1       | <---------> |         10.20X.1.2        | <---------> |       10.201.99.4       |
+-------------------------+             +---------------------------+             +-------------------------+
```

**Supported Devices in One-DuT (`dX`):**
- `d2`: Gowin GW-BS-1UR2-25G (`10.202.1.2`)
- `d3`: Macchiato MACCHIATObin Double Shot (`10.203.1.2`)
- `d4`: Banana Pi R4 2x10G SFP+ (`10.204.1.2`)
- `d5`: Puzzle IEI PUZZLE-M902 (`10.205.1.2`)
- `d6`: Banana Pi R64 (`10.206.1.2`)
- `d7`: Lumen Quantum Fiber W1700K (`10.207.1.2`)
<br><br>

## IP Address Configuration

The following diagrams show WireGuard addressing examples. Each protocol family
uses its own IPv4 prefix: `10.20X` for plaintext, `10.21X` for WireGuard,
`10.22X` for WolfGuard, and `10.23X` for MACsec, where `X` is `1` for the
two-DuT setup or the one-DuT profile number (`2` through `7`). The plaintext
and MACsec layouts are described separately below. Addresses in these examples
belong to the data plane; the architecture diagrams above show inventory host
addresses.

### Two-DuT Setup

```text
+--------------+           +--------------------------------------------------+                  +--------------------------------------------------+           +--------------+
|    Source    |           |                    Encryptor                     |                  |                   Decryptor                      |           |     Sink     |
|--------------|           |--------------------------------------------------|                  |--------------------------------------------------|           |--------------|
|         eth0 | Plaintext | eth1         |        wgX         |         eth0 | WireGuard Tunnel | eth1         |        wgX         |         eth0 | Plaintext | eth0         |
| 10.211.100.1 | --------> | 10.211.100.2 |  10.211.0.1 (wg0)  | 10.211.199.1 | ---------------> | 10.211.199.2 |  10.211.0.2 (wg0)  | 10.211.200.2 | --------> | 10.211.200.1 |
| 10.211.101.1 | --------> | 10.211.101.2 |  10.211.1.1 (wg1)  |              | ---------------> |              |  10.211.1.2 (wg1)  | 10.211.201.2 | --------> | 10.211.201.1 |
| 10.211.102.1 | --------> | 10.211.102.2 |  10.211.2.1 (wg2)  |              | ---------------> |              |  10.211.2.2 (wg2)  | 10.211.202.2 |           | 10.211.202.1 |
|      ...     |           |      ...     |        ....        |              |                  |              |        ....        |      ...     |           |      ...     |
| 10.211.131.1 | --------> | 10.211.131.2 | 10.211.31.1 (wg31) |              | ---------------> |              | 10.211.31.2 (wg31) | 10.211.231.2 | --------> | 10.211.231.1 |
+--------------+           +--------------------------------------------------+                  +--------------------------------------------------+           +--------------+
```

The plaintext baseline uses the same four-device path, with static routing and
MTU 1500. Each flow has its own middle-link subnet on the encryptor's `wg_source`
(`eth0`) and decryptor's `wg_sink` (`eth1`); it requires no tunnel interfaces or keys.

| Flow | Source / Encryptor source link | Encryptor / Decryptor middle link | Decryptor / Sink link |
| --- | --- | --- | --- |
| 0 | `10.201.100.1` / `10.201.100.2` | `10.201.0.1` / `10.201.0.2` | `10.201.200.2` / `10.201.200.1` |
| 1 | `10.201.101.1` / `10.201.101.2` | `10.201.1.1` / `10.201.1.2` | `10.201.201.2` / `10.201.201.1` |
| 31 | `10.201.131.1` / `10.201.131.2` | `10.201.31.1` / `10.201.31.2` | `10.201.231.2` / `10.201.231.1` |

All IPv4 links use `/30`. For flow `n`, IPv6 uses `10:201:(100+n)::/126`
on the source link, `10:201:n::/126` on the middle link, and
`10:201:(200+n)::/126` on the sink link, with the same host suffixes as IPv4.
The formulas insert the index as text into IPv6 hextets, preserving the existing
addressing convention. Static forward and return routes use each flow's next hop
for both address families. The lab must permit IP forwarding and firewall forwarding
across these interfaces.

MACsec uses the same four-device routing layout with subnet base `230`: device 1
uses `10.231`, while the one-DuT profiles use `10.232` through `10.237`.
For two-DuT flow `n`, the addresses are:

| Link | Subnet | First endpoint | Second endpoint |
| --- | --- | --- | --- |
| Source → Encryptor | `10.231.(100+n).0/30` | Source `.1` | Encryptor `.2` |
| Encryptor → Decryptor | `10.231.n.0/30` | Encryptor `.1` | Decryptor `.2` |
| Decryptor → Sink | `10.231.(200+n).0/30` | Sink `.1` | Decryptor `.2` |

The middle-link interfaces are `macsec0` through `macsec31`, on encryptor `eth0`
and decryptor `eth1`. Each has TX/RX association sections and a static
`macsecN_network` interface using `@macsecN`. IPv6 follows the existing `/126`
convention, with explicit forward and return routes.

The one-DuT profiles place MACsec on the DuT's sink-facing device and the sink's
existing VLAN device. Their encrypted link uses `10.23X.(200+n).0/30`, with sink
`.1` and DuT `.2`; the source link uses `10.23X.(100+n).0/30`. Sink interface names
are scoped by profile, such as `d2_macsec0`.

Each MACsec interface also has a `config device` section setting its MAC address
to `02:00:00:PP:EE:NN`. All fields are hexadecimal: `PP` is `01` for two-DuT
or the profile number (`02` for `d2`, etc.); `EE` is `01` for the encryptor/DuT
and `02` for the decryptor/sink; `NN` is the zero-based interface index.
Thus two-DuT `macsec0` uses `02:00:00:01:01:00` on the encryptor and
`02:00:00:01:02:00` on the decryptor, while `macsec31` ends in `1f`.
Device sections are named `macsecN_device` (or `dX_macsecN_device` on the sink)
so they coexist with the interface sections in UCI. These device MAC addresses
are configured separately from the explicit SCI identifiers below.

MACsec defaults to each topology's configured CPU/flow count: 32 for two-DuT,
8 for `d2`, 4 for `d3`–`d5`, 2 for `d6`, and 4 for `d7`. These are configured
limits, not CPU detection on the controller. Set `count` on a MACsec family to
use fewer interfaces; it must not exceed the enclosing count. The current
`200+n` IPv4 formula supports at most 56 interfaces.

MACsec protocol interfaces are disabled by default (`option disabled '1'`).
Set `disabled` to `0` on an interface in OpenWrt to enable it after deployment.
MACsec uses `gcm-aes-xpn-256`, software encryption (`offload off`), association
number 0, and replay protection disabled, matching the supplied lab configuration.
The default MACsec MTU is 1468 to accommodate its 32-byte overhead on a
1500-byte parent; a family `mtu` override is available. Each channel has a stable
explicit SCI, whose final two bytes encode port `n+1`, and the peer's RX SCI
matches it. Explicit SCI replaces the interface `port` option and avoids requiring
physical NIC MAC addresses in the topology. OpenWrt must have the `macsec`
protocol handler with explicit SCI/XPN support, `kmod-macsec`, and `ip-full`.

### One-DuT Setup

```text
+--------------+           +--------------------------------------------------+                  +-----------------------------------+
|    Source    |           |             Encryptor / Decryptor dX             |                  |                Sink               |
|--------------|           |--------------------------------------------------|                  |-----------------------------------|
|    eth1.120X | Plaintext | if_src       |         wgY        |      if_sink | WireGuard Tunnel | eth1.220X    |         wgY        |
| 10.21X.100.1 | <-------> | 10.21X.100.2 | 10.21X.200.2 (wg0) | 10.21X.200.2 | <--------------> | 10.21X.200.1 | 10.21X.200.1 (wg0) |
| 10.21X.101.1 | <-------> | 10.21X.101.2 | 10.21X.201.2 (wg1) | 10.21X.201.2 | <--------------> | 10.21X.201.1 | 10.21X.201.1 (wg1) |
| 10.21X.102.1 | <-------> | 10.21X.102.2 | 10.21X.202.2 (wg2) | 10.21X.202.2 | <--------------> | 10.21X.202.1 | 10.21X.202.1 (wg2) |
|      ...     |           |      ...     |         ...        |      ...     |                  |      ...     |         ...        |
| 10.21X.107.1 | <-------> | 10.21X.107.2 | 10.21X.207.2 (wg7) | 10.21X.207.2 | <--------------> | 10.21X.207.1 | 10.21X.207.1 (wg7) |
+--------------+           +--------------------------------------------------+                  +-----------------------------------+
```

All per-flow IPv4 links use `/30`. In the current one-DuT configuration,
WireGuard and WolfGuard underlay and tunnel interfaces use the same per-flow
addresses. The `wg7` row applies to the eight-flow `d2` profile; other profiles
use their configured flow counts. VLAN parents use MTU 9000, while source and
sink VLAN devices use MTU 1500.
<br><br>

## What is Generated?

This Ansible automation relies on `topology/topology.yml` and custom Python scripts to generate what is needed for the data-plane. It intentionally avoids touching management interfaces.

The following configurations are generated:
- Arch Linux source NetworkManager keyfiles.
- OpenWrt static interfaces for source/sink.
- WireGuard and WolfGuard tunnels (keys, interfaces, peers).
- MACsec interfaces, paired TX/RX associations, static IP interfaces, and routes.
- Shared sink return routes.
<br><br>

## Configuration Files

The repository relies on several YAML configuration files to define the testing environment and Ansible behavior:

- **`topology/topology.yml`**: The core configuration file that defines the test topologies (`two_dut` and `one_dut`), hosts (and their roles), protocols (Plaintext, WireGuard, WolfGuard, MACsec), subnet bases, prefix lengths, and interface mappings for each specific Device under Test.
- **`inventories/lab/hosts.yml`**: Maps the physical or virtual hosts to Ansible groups (like `source`, `sink`, `enc`, `dec`, and the various one-DuT devices) and sets connection variables.
- **`requirements.yml`**: Specifies the required Ansible Galaxy collections needed to run the playbooks.

The traffic source host uses NetworkManager keyfiles. The inventory assumes the source host is the Ansible controller itself (`ansible_connection: local`). Change this in `inventories/lab/hosts.yml` if your control node is separate.
<br><br>

## Key Generation

WireGuard and WolfGuard keys can be generated using standard tooling. By default, the playbook attempts to use:
- **WireGuard**: `wg-wireguard`, falling back to `wg`
- **WolfGuard**: `wg-fips`

You can manually trigger key generation or override the tools using environment variables:

```bash
WG_KEYGEN_TOOL=wg-wireguard WOLFGUARD_KEYGEN_TOOL=wg-fips ansible-playbook playbooks/generate_keys.yml
```

The same playbook generates independent random 256-bit MACsec TX keys, 128-bit
key IDs, 96-bit XPN salts, and 32-bit SSCIs for each endpoint and interface.
The peer's RX association uses the corresponding TX material. MACsec requires
no external key generation tool. Material is stored under `generated_macsec_keys`
in `inventories/lab/generated/keys.yml`, with file permissions `0600`; existing
WireGuard/WolfGuard and MACsec keys are preserved on ordinary generation runs.
Run key generation again after adding MACsec to an existing lab.

These manually keyed associations start at packet number 1. Before recreating
channels that have already carried traffic (including after a reboot), rotate
their keys and salts on both endpoints to avoid reusing an AES-GCM nonce. The
existing force option rotates all configured protocols:

```bash
ansible-playbook playbooks/generate_keys.yml -e generate_key_extra_args=--force
```

Local previews can use `CHANGE_ME` placeholders when MACsec keys are absent;
deployment requires generated keys.
<br><br>

## Usage

1. **Install dependencies:**
   ```bash
   ansible-galaxy collection install -r requirements.yml
   ```

2. **Generate cryptographic keys:**
   ```bash
   ansible-playbook playbooks/generate_keys.yml
   ```

3. **Render configurations locally (optional, for preview):**
   ```bash
   ansible-playbook playbooks/render_local.yml
   ```
   Preview the generated configs:
   ```bash
   less rendered/sink/network.fragment
   less rendered/d3/apply-network.sh
   less rendered/source/system-connections/D1-Supermicro.nmconnection
   ```

4. **Deploy to the Lab Environment:**
   Run the full site playbook or target specific devices:
   ```bash
   ansible-playbook playbooks/site.yml
   ```
   Or individually:
   ```bash
   ansible-playbook playbooks/source.yml  # Arch source NetworkManager keyfiles
   ansible-playbook playbooks/dut.yml     # OpenWrt DUTs
   ansible-playbook playbooks/sink.yml    # OpenWrt sink
   ```
