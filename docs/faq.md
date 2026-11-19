# Frequently Asked Questions (FAQ)

### What is Ticket-to-Topology?
Ticket-to-Topology (`t2t`) is a dual-mode training simulator and audit platform for Cisco IOS-XE enterprise networks, focusing on mutual route redistribution between EIGRP and OSPF.

### Can I run this without live routers?
Yes! Passing the `--replay` flag (or running `t2t demo`) runs all commands, checks, and audits offline using recorded or synthetic fixture files. No hardware or virtualization software is required.

### How does the grading engine ensure fairness?
Technical verification (PASS/FAIL) is 100% deterministic, based on real route lookups, reachability tests, and configuration diffs. The AI layer is strictly used for mentor guidance, ticket text, and non-authoritative explanation feedback.

### Why is mutual redistribution dangerous?
When multiple boundary routers (ASBRs) redistribute between autonomous systems, routes redistributed into one domain can be advertised back into the original domain. This can cause routing loops or suboptimal paths unless loop-prevention route tags and administrative distance overrides are properly deployed.

### Which audit rules are checked?
The audit engine checks 7 core rules (A1–A7) including:
- Redistributing without a route-map (A1)
- Missing EIGRP seed metric (A2)
- Missing OSPF `subnets` keyword (A3)
- Missing route tag loop guards across ASBRs (A4)
- Mismatched or default OSPF external administrative distance (A5)
- Route-map permit clauses or missing ACLs/prefix-lists (A6)
- Mismatched OSPF external metric-types (A7)
