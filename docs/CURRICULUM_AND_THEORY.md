# Curriculum Alignment & Routing Redistribution Theory

> **A Comprehensive Academic & Theoretical Guide to Multi-Point Mutual Route Redistribution, Administrative Distance Inversion, and Routing Loop Prevention on Cisco IOS-XE Networks**

---

## 1. Academic & Industry Curriculum Context

### 1.1 Cisco Certified Network Professional (CCNP) Enterprise
The **Ticket-to-Topology (`t2t`)** project addresses core objectives from the Cisco CCNP Enterprise certification track:

1. **ENCOR 350-401 (Implementing and Operating Cisco Enterprise Network Core Technologies)**:
   * **Domain 3.0: Infrastructure**
     * *3.2: Configure and verify route redistribution between any routing protocols.*
     * *3.3: Configure and verify manual summarization, default routing, and policy-based routing.*
     * *3.4: Configure and verify administrative distance and metric weights.*
2. **ENARSI 300-410 (Implementing Cisco Enterprise Advanced Routing and Services)**:
   * **Domain 1.0: Layer 3 Technologies**
     * *1.1: Troubleshoot administrative distance (all routing protocols).*
     * *1.2: Troubleshoot route redistribution between any routing protocols (RIP, EIGRP, OSPF, and BGP).*
     * *1.3: Troubleshoot routing loop prevention mechanisms (route tagging, route-maps, and prefix-lists).*
     * *1.4: Troubleshoot suboptimal routing caused by asymmetric metric translation.*

### 1.2 NPTEL & University B.Tech Curriculum
In academic degree programs (Computer Science and Engineering / Information Technology):
* **Advanced Computer Networks / Enterprise Networking**: Covers autonomous system interconnection, interior gateway protocol interoperability, convergence time optimization, and link-state versus distance-vector trade-offs.
* **Capstone Software & Systems Engineering**: Applying software engineering methodologies (AST grammar parsing, state machines, automated testing, static code analysis) to solve complex infrastructure engineering problems.

---

## 2. Theoretical Foundations: EIGRP vs. OSPF

Interior Gateway Protocols (IGPs) are divided into distinct algorithmic families that do not share metric spaces or control-plane convergence rules.

```
+------------------------------------+------------------------------------+
| Enhanced Interior Gateway (EIGRP)  | Open Shortest Path First (OSPF)    |
+------------------------------------+------------------------------------+
| Algorithmic Family: Advanced       | Algorithmic Family: Link-State     |
| Distance-Vector (DUAL)             | (Dijkstra's Shortest Path First)   |
| Metric Type: 32-bit (or 64-bit)    | Metric Type: Dimensionless Cost    |
| Composite Vector                   | based on Reference Bandwidth       |
| Metric Ingredients: Bandwidth,     | Metric Ingredients: Inverse        |
| Delay, Reliability, Load, MTU      | Interface Bandwidth only           |
| Administrative Distance:           | Administrative Distance:           |
| - Internal: 90                     | - Intra-area: 110                  |
| - External (Redistributed): 170    | - Inter-area: 110                  |
| - Summary: 5                       | - External (E1 / E2): 110          |
| Loop Prevention: Feasibility       | Loop Prevention: Shortest Path     |
| Condition (RD < FD) within domain  | Tree (SPF) within Area 0 backbone  |
+------------------------------------+------------------------------------+
```

### 2.1 EIGRP Composite Metric Calculation
EIGRP determines path cost using a composite formula governed by $K$-values ($K_1=1, K_2=0, K_3=1, K_4=0, K_5=0$ by default):

$$\text{Metric} = \left[ K_1 \cdot \text{Scaled Bandwidth} + \frac{K_2 \cdot \text{Scaled Bandwidth}}{256 - \text{Load}} + K_3 \cdot \text{Scaled Delay} \right] \cdot \left[ \frac{K_5}{\text{Reliability} + K_4} \right] \cdot 256$$

Under default $K$-values, this simplifies to:

$$\text{Metric} = 256 \cdot \left( \frac{10^7}{\text{Minimum Bandwidth (kbps)}} + \frac{\text{Total Cumulative Delay (microseconds)}}{10} \right)$$

### 2.2 OSPF Link-State Cost Calculation
OSPF assigns an interface cost proportional to the inverse of bandwidth:

$$\text{Cost} = \frac{\text{Reference Bandwidth}}{\text{Interface Bandwidth}}$$

By default, Cisco IOS-XE uses a reference bandwidth of $100\text{ Mbps}$ ($10^8\text{ bps}$). A GigabitEthernet interface has cost $1$, FastEthernet has cost $1$, and a $10\text{ Mbps}$ link has cost $10$.

---

## 3. The Redistribution Dilemma in Dual-ASBR Topologies

When connecting two routing domains at a **single point of redistribution** (single ASBR), redistribution is trivial. However, a single ASBR represents a single point of failure. Enterprise networks require **multi-point (dual-ASBR) redistribution** for high availability and fault tolerance.

```
       +------------------------------------------------------------+
       |                        EIGRP DOMAIN                        |
       |                           AS 100                           |
       |                                                            |
       |                    +------------------+                    |
       |                    |    R1 (Branch)   |                    |
       |                    |  10.10.1.0/24    |                    |
       |                    +------------------+                    |
       |                        /          \                        |
       |             10.1.12.0 /            \ 10.1.13.0             |
       |                      /              \                      |
       +---------------------|----------------|---------------------+
                             |                |
                     +---------------+  +---------------+
                     |   R2 (ASBR)   |  |   R3 (ASBR)   |
                     |  EIGRP <->OSPF|  |  EIGRP <->OSPF|
                     +---------------+  +---------------+
                             |   10.1.23.0/24 | (Inter-ASBR Link)
                             | (Backdoor Link)|
       +---------------------|----------------|---------------------+
       |                      \              /                      |
       |             10.1.24.0 \            / 10.1.34.0             |
       |                        \          /                        |
       |                    +------------------+                    |
       |                    |     R4 (HQ)      |                    |
       |                    |  10.10.99.0/24   |                    |
       |                    +------------------+                    |
       |                                                            |
       |                        OSPF DOMAIN                         |
       |                          Area 0                            |
       +------------------------------------------------------------+
```

In the topology above, R2 and R3 simultaneously perform **mutual redistribution**:
1. EIGRP routes are redistributed into OSPF.
2. OSPF routes are redistributed into EIGRP.

Without rigorous policy engineering, this architecture suffers from three catastrophic failures:

---

### Hazard 1: Loss of Metric Semantics (The Metric Translation Problem)
Because EIGRP metric components (bandwidth and delay) cannot map into an OSPF scalar cost, and vice-versa, the router has no native way to calculate the cost of a redistributed route.

* **EIGRP into OSPF**: Cisco IOS-XE defaults to assigning an OSPF Type-2 external metric of $20$ (or $1$ for BGP). Crucially, the router will **only redistribute classful network boundaries** unless the `subnets` keyword is explicitly specified:
  ```cisco
  ! Fails to redistribute /24 subnets of 10.0.0.0:
  router ospf 1
   redistribute eigrp 100
  
  ! Correct:
  router ospf 1
   redistribute eigrp 100 subnets
  ```
* **OSPF into EIGRP**: EIGRP does **not** have a default seed metric. If you configure `redistribute ospf 1` without specifying composite metrics, the routes are assigned a metric of **infinity** and are silently dropped! EIGRP demands explicit seed parameters:
  ```cisco
  router eigrp 100
   redistribute ospf 1 metric 10000 100 255 1 1500
   ! Or globally:
   default-metric 10000 100 255 1 1500
  ```

---

### Hazard 2: Administrative Distance Inversion & Suboptimal Routing

Administrative Distance (AD) determines which routing protocol is installed into the Routing Information Base (RIB) when the exact same prefix is learned via multiple protocols. Lower AD is strictly preferred.

```
Cisco IOS-XE Administrative Distance Rankings:
Connected:            0
Static:               1
EIGRP Summary:        5
eBGP:                20
EIGRP Internal:      90   <--- Native EIGRP routes
OSPF (all types):   110   <--- OSPF intra, inter, and external routes
IS-IS:              115
RIP:                120
EIGRP External:     170   <--- Redistributed EIGRP routes
iBGP:               200
```

#### The Suboptimal Routing Cascade:
1. R4 advertises prefix `10.10.99.0/24` into OSPF Area 0.
2. Both R2 and R3 learn `10.10.99.0/24` via native OSPF with $\text{AD} = 110$.
3. R2 redistributes `10.10.99.0/24` into EIGRP AS 100.
4. In EIGRP, redistributed routes are flagged as **External**, which carries an administrative distance of **$\text{AD} = 170$**.
5. R2 advertises this external EIGRP route to R1, which in turn advertises it to R3.
6. Now, consider the routing table on R3:
   * Direct path from R4 via OSPF: $\text{AD} = 110$
   * Path from R1 via EIGRP External: $\text{AD} = 170$
7. Because $110 < 170$, R3 prefers the OSPF path. That is fine so far.
8. **Now consider the reverse**: Prefix `10.10.1.0/24` on R1 (Branch).
   * R1 advertises `10.10.1.0/24` via native EIGRP ($\text{AD} = 90$).
   * Both R2 and R3 learn `10.10.1.0/24` with $\text{AD} = 90$.
   * R2 redistributes `10.10.1.0/24` into OSPF with $\text{AD} = 110$.
   * R2 advertises this OSPF route across the inter-ASBR link (`10.1.23.0/24`) to R3.
   * If R3's native EIGRP link to R1 fluctuates or is configured with high delay, R3 might prefer the OSPF route through R2!
   * Even worse: on ASBRs redistributing multiple external protocols, an external EIGRP route ($\text{AD} = 170$) will **always be beaten** by an OSPF external route ($\text{AD} = 110$) for the same prefix, creating an Administrative Distance Inversion!

---

### Hazard 3: Circular Route Feedback Loops

When R2 redistributes an EIGRP route into OSPF, the route is announced across the OSPF domain and reaches R3. If R3 is also redistributing OSPF into EIGRP, R3 will receive this route, fail to realize it originally came from EIGRP, and **re-advertise it back into EIGRP**!

```
[R1: 10.10.1.0] 
       | (EIGRP Native, Metric 28160)
       v
    [R2: ASBR] === redistributes ===> [OSPF Domain: Cost 20]
                                              |
                                              v
    [R3: ASBR] <== re-injects OSPF === [OSPF Domain]
       | (EIGRP External, Metric 2816000)
       v
[R1 receives its OWN route back with higher metric!]
```

When routes bounce between ASBRs:
1. Routing metrics get overwritten at each boundary.
2. The original path characteristics (hops, bandwidth) are erased.
3. Routers install circular next-hops ($R2 \rightarrow R3 \rightarrow R2$), creating **micro-loops** that consume 100% link bandwidth and drop packets upon IP Time-To-Live (TTL) expiration.

---

## 4. Engineering Solutions & Best Practices

To achieve stable, loop-free, optimal mutual redistribution, network engineers combine three distinct control-plane techniques:

### Solution 1: Route Tagging with Route-Maps
Every route redistributed into a peer protocol is stamped with a 32-bit numerical tag. The peer ASBR inspects the tag and refuses to re-inject routes carrying that tag.

```cisco
! ==========================================================
! Configuration on R2 (Primary ASBR)
! ==========================================================

! 1. Tag routes entering OSPF from EIGRP with Tag 110
route-map EIGRP_TO_OSPF permit 10
 set tag 110

! 2. Deny routes entering EIGRP if they already carry Tag 120 (from R3)
route-map OSPF_TO_EIGRP deny 10
 match tag 120
route-map OSPF_TO_EIGRP permit 20
 set tag 210

! 3. Apply route-maps to redistribution
router eigrp 100
 default-metric 10000 100 255 1 1500
 redistribute ospf 1 route-map OSPF_TO_EIGRP

router ospf 1
 redistribute eigrp 100 subnets route-map EIGRP_TO_OSPF
```

```cisco
! ==========================================================
! Configuration on R3 (Secondary ASBR)
! ==========================================================

! 1. Tag routes entering OSPF from EIGRP with Tag 120
route-map EIGRP_TO_OSPF permit 10
 set tag 120

! 2. Deny routes entering EIGRP if they carry Tag 110 (from R2)
route-map OSPF_TO_EIGRP deny 10
 match tag 110
route-map OSPF_TO_EIGRP permit 20
 set tag 220

! 3. Apply route-maps to redistribution
router eigrp 100
 default-metric 10000 100 255 1 1500
 redistribute ospf 1 route-map OSPF_TO_EIGRP

router ospf 1
 redistribute eigrp 100 subnets route-map EIGRP_TO_OSPF
```

---

### Solution 2: Administrative Distance Tuning
To resolve the AD Inversion problem where OSPF external ($\text{AD} = 110$) defeats EIGRP external ($\text{AD} = 170$), the ASBR's distance for OSPF external routes can be tuned above $170$:

```cisco
router ospf 1
 ! Syntax: distance ospf external <metric> intra-area <metric> inter-area <metric>
 distance ospf external 171
```

* **Effect**: OSPF internal routes retain $\text{AD} = 110$. OSPF external (E1/E2) routes receive $\text{AD} = 171$.
* **Result**: On both R2 and R3, an EIGRP external route ($\text{AD} = 170$) will now be preferred over a redistributed OSPF external route ($170 < 171$), preventing suboptimal routing!

---

### Solution 3: Prefix-List Boundaries
In addition to tags, mission-critical subnets should be explicitly permitted or denied using IP Prefix-Lists to guarantee that internal loopback addresses or transit management subnets are never leaked:

```cisco
ip prefix-list HQ_NETWORKS permit 10.10.99.0/24
ip prefix-list BRANCH_NETWORKS permit 10.10.1.0/24

route-map OSPF_TO_EIGRP permit 20
 match ip address prefix-list HQ_NETWORKS
 set metric 10000 100 255 1 1500
```

---

## 5. Summary: How `t2t` Validates These Principles

The Ticket-to-Topology platform encodes every single one of these theoretical principles into software:
* **The AST Parser** extracts the exact `route-map`, `prefix-list`, `distance`, and `redistribute` statements into an object tree.
* **The Static Audit Engine** verifies that Rules A1 through A7 enforce seed metrics, tagging, and distance tuning.
* **The Verification Oracle** evaluates the resulting routing table to confirm that no AD inversion or circular feedback occurs in practice.
