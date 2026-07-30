# WireGuard eBPF Ansible

This repository contains an Ansible-based automation suite for configuring a lab environment to benchmark and compare the throughput of WireGuard kernel implementation against eBPF/XDP and eBPF/TC. It also supports baseline Plaintext and WolfGuard traffic.

It defines network topologies, manages keys, and generates configurations for Arch Linux and OpenWrt devices under test (DuTs).
<br><br>

## Architecture and Topologies

The lab environment supports two primary network topologies, modeling different test setups.
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
| Supermicro / Arch Linux |  Plaintext  |  Supermicro / OpenWrt  |  WireGuard  |  Supermicro / OpenWrt  |  Plaintext  |  Supermicro / OpenWrt   |
|       10.201.99.1       | ----------> |      10.201.99.2       | ----------> |      10.201.99.3       | ----------> |       10.201.99.4       |
+-------------------------+             +------------------------+             +------------------------+             +-------------------------+
```

### 2. One-DuT Setup (`one_dut`)

A one DuT / three-device setup where a single Device under Test (DuT) handles the offloading.

```text
+-------------------------+             +---------------------------+             +-------------------------+
|     Traffic Source      |             | Encryptor / Decryptor DuT |             |      Traffic Sink       |
| Supermicro / Arch Linux |  Plaintext  |        dX / OpenWrt       |  WireGuard  |  Supermicro / OpenWrt   |
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

The following diagrams illustrate the IP addressing scheme used for the tunnel setups.

### Two-DuT Setup

```text
+--------------+           +--------------------------------------------------+                  +--------------------------------------------------+           +--------------+
|    Source    |           |                    Encryptor                     |                  |                   Decryptor                      |           |     Sink     |
|--------------|           |--------------------------------------------------|                  |--------------------------------------------------|           |--------------|
|         eth0 | Plaintext | eth1         |        wgX         |         eth0 | WireGuard Tunnel | eth1         |        wgX         |         eth0 | Plaintext | eth0         |
| 10.201.100.1 | --------> | 10.201.100.2 |  10.211.0.1 (wg0)  | 10.211.199.1 | ---------------> | 10.211.199.2 |  10.211.0.2 (wg0)  | 10.201.200.2 | --------> | 10.201.200.1 |
| 10.201.101.1 | --------> | 10.201.101.2 |  10.211.1.1 (wg1)  |              | ---------------> |              |  10.211.1.2 (wg1)  | 10.201.201.2 | --------> | 10.201.201.1 |
| 10.201.102.1 | --------> | 10.201.102.2 |  10.211.2.1 (wg2)  |              | ---------------> |              |  10.211.2.2 (wg2)  | 10.201.202.2 |           | 10.201.202.1 |
|      ...     |           |      ...     |        ....        |              |                  |              |        ....        |      ...     |           |      ...     |
| 10.201.131.1 | --------> | 10.201.131.2 | 10.211.31.1 (wg31) |              | ---------------> |              | 10.211.31.2 (wg31) | 10.201.231.2 | --------> | 10.201.231.1 |
+--------------+           +--------------------------------------------------+                  +--------------------------------------------------+           +--------------+
```

### One-DuT Setup

```text
+--------------+           +--------------------------------------------------+                  +-----------------------------------+
|    Source    |           |             Encryptor / Decryptor dX             |                  |                Sink               |
|--------------|           |--------------------------------------------------|                  |-----------------------------------|
|    eth1.120X | Plaintext | if_src       |         wgY        |      if_sink | WireGuard Tunnel | eth1.220X    |         wgY        |
| 10.20X.100.1 | <-------> | 10.20X.100.2 | 10.21X.200.2 (wg0) | 10.21X.199.2 | <--------------> | 10.21X.199.1 | 10.21X.200.1 (wg0) |
| 10.20X.101.1 | <-------> | 10.20X.101.2 | 10.21X.201.2 (wg1) | 10.21X.198.2 | <--------------> | 10.21X.198.1 | 10.21X.201.1 (wg1) |
| 10.20X.102.1 | <-------> | 10.20X.102.2 | 10.21X.202.2 (wg2) | 10.21X.197.2 | <--------------> | 10.21X.197.1 | 10.21X.202.1 (wg2) |
|      ...     |           |      ...     |         ...        |      ...     |                  |      ...     |         ...        |
| 10.20X.107.1 | <-------> | 10.20X.107.2 | 10.21X.207.2 (wg7) | 10.21X.192.2 | <--------------> | 10.21X.192.1 | 10.21X.207.1 (wg7) |
+--------------+           +--------------------------------------------------+                  +-----------------------------------+
```
<br><br>

## What is Generated?

This Ansible automation relies on `topology/topology.yml` and custom Python scripts to generate what is needed for the data-plane. It intentionally avoids touching management interfaces.

The following configurations are generated:
- Arch Linux source NetworkManager keyfiles.
- OpenWrt static interfaces for source/sink.
- WireGuard and WolfGuard tunnels (keys, interfaces, peers).
- Shared sink return routes.
<br><br>

## Configuration Files

The repository relies on several YAML configuration files to define the testing environment and Ansible behavior:

- **`topology/topology.yml`**: The core configuration file that defines the test topologies (`two_dut` and `one_dut`), hosts (and their roles), protocols (Plaintext, WireGuard, WolfGuard), subnet bases, prefix lengths, and interface mappings for each specific Device under Test.
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
