# Lab Environment Guide

This guide describes how to connect `t2t` to a live physical or virtualised network topology (EVE-NG, Cisco CML, GNS3, or physical hardware).

---

## 1. Network Topology

The reference CCNP Enterprise lab consists of four routers running Cisco IOS-XE:

- **R1 (Branch):** Loopbacks `10.10.1.1/24`, `10.10.2.1/24`, `10.10.99.1/24`. Runs EIGRP AS 100.
- **R2 (ASBR 1):** Connects to R1 (`10.1.12.0/24`) and R4 (`10.1.24.0/24`). Mutual redistribution between EIGRP 100 and OSPF 1.
- **R3 (ASBR 2):** Connects to R1 (`10.1.13.0/24`) and R4 (`10.1.34.0/24`). Redundant mutual redistribution with loop-prevention route tags.
- **R4 (HQ Core):** Loopbacks `172.16.10.1/24`, `172.16.20.17/28`. Runs OSPF 1 Area 0.

---

## 2. Lab Configuration (`lab/inventory.yaml`)

Copy `lab/inventory.example.yaml` to `lab/inventory.yaml` and configure management IPs:

```yaml
defaults:
  device_type: cisco_xe
  golden_path: "flash:golden.cfg"

routers:
  - name: R1
    host: 192.168.100.11
    role: branch
  - name: R2
    host: 192.168.100.12
    role: asbr
  - name: R3
    host: 192.168.100.13
    role: asbr
  - name: R4
    host: 192.168.100.14
    role: hq
```

---

## 3. Environment Variables (`.env`)

Store credentials securely in `.env` (never commit this file):

```bash
LAB_USERNAME=cisco
LAB_PASSWORD=cisco123!
T2T_INVENTORY=lab/inventory.yaml
T2T_AI_PROVIDER=none   # or gemini, openai, ollama
```

---

## 4. Pre-Flight Verification

Validate management reachability, authentication, and IOS-XE prerequisites:
```bash
t2t doctor
```
All four routers must report `PASS` across TCP 22, Login, IOS-XE Release, Golden File, Archive, and VRF MGMT.
