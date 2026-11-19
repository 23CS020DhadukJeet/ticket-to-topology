# Learning Guide: Tips, Tricks & Mental Models for Ticket-to-Topology

> **Intuitive Analogies, Practical Tips, and Step-by-Step Guidance for Students, Engineers, and Instructors**

---

## 1. Route Redistribution in Plain English: 3 Intuitive Analogies

If you find routing protocol redistribution difficult to wrap your head around, use these real-world analogies:

### Analogy 1: The Two Translators (Why We Need Seed Metrics)
Imagine two people in an international meeting:
* Alice speaks **French** (EIGRP). In French, she describes distance in *kilometers and travel time*.
* Bob speaks **Japanese** (OSPF). In Japanese, he describes distance as *cost in Yen*.
* Charlie and Dave are **bilingual translators** sitting between them (the ASBR routers R2 and R3).

When Alice says *"The branch office is 100 km away and takes 10 milliseconds"* (composite vector metric), Charlie must translate that into Japanese for Bob.
* If Charlie just passes the message to Bob without an exchange formula or metric, Bob has no idea what "100 km" means in Yen. Bob throws the paper away (the route is dropped!).
* **The Fix**: Charlie must explicitly state: *"In Yen, this costs 20 units"* (`default-metric` or `metric` seed).

---

### Analogy 2: The Infinite Echo / Gossip Loop (Why We Need Route Tagging)
Now imagine Charlie translates Alice's French message into Japanese and shouts it into the Japanese room.
* Dave (the second translator) hears Charlie's Japanese translation.
* Dave thinks: *"Oh, a new Japanese route! Let me be helpful and translate this back into French for Alice!"*
* Alice receives her own message back, but now it says *"From Dave, cost is higher"*.
* Charlie hears Dave's French message and translates it *back* into Japanese again!
* The message bounces between Charlie and Dave in an **infinite loop**, drowning out all real conversation.
* **The Fix (Route Tagging)**: When Charlie translates Alice's French message into Japanese, he sticks a **blue sticky note** on it (`set tag 110`). When Dave sees any message with a blue sticky note, his rule says: *"DO NOT translate this back into French!"* (`match tag 110` -> `deny`). The loop is broken!

---

### Analogy 3: The Trust Hierarchy (Why Administrative Distance Inversion Happens)
Imagine a company where employees follow a strict trust hierarchy:
* Direct eyewitness reports from close colleagues (Native EIGRP): **Trust Level 90** (High trust).
* Reports from the corporate intranet newsboard (Native OSPF): **Trust Level 110** (Medium trust).
* Rumors heard second-hand from an outside consultant (External Redistributed EIGRP): **Trust Level 170** (Low trust).

Now, notice what happens when a message from the branch office is redistributed into OSPF:
1. It becomes a newsboard post (OSPF). The router trusts the newsboard at **Level 110**.
2. But the second ASBR also hears the route from the branch via external EIGRP (**Level 170**).
3. The router says: *"Level 110 is more trustworthy than Level 170!"*
4. So instead of sending the packet directly to the branch, it sends it across the building to the other ASBR!
5. **The Fix (`distance ospf external 171`)**: We tell the router: *"Treat outside consultant reports on OSPF at Trust Level 171 (even lower trust than EIGRP 170)."* Now, the router prefers direct EIGRP ($170 < 171$)!

---

## 2. Practical Tips to Score 100/100 in the Simulator

When solving a troubleshooting ticket (e.g. `t2t new-ticket --fault T3`):

### Tip 1: Run `t2t audit` FIRST
Before writing a single line of Cisco configuration, run:
```bash
t2t audit
```
* The static audit engine inspects the AST across all routers in milliseconds.
* Look at the output table: it immediately tells you if a default seed metric is missing (Rule A1), if route tagging is absent (Rule A3), or if AD inversion is present (Rule A5).
* This eliminates 90% of blind guessing!

### Tip 2: Keep Your Remediation Minimal (Avoid AST Anti-Drift Penalties)
* The scoring engine compares your submitted configuration with the canonical fix using **AST Levenshtein distance**.
* **Do NOT** paste your entire router configuration.
* **Do NOT** rename route-maps or create 5 unnecessary access-lists.
* Only submit the exact commands needed to fix the defect.
  * *Example Good Submission*:
    ```bash
    t2t submit --replay -e "router ospf 1\n distance ospf external 171"
    ```
  * *Example Bad Submission*: Pasting 40 lines of interface descriptions, NTP settings, and DNS lookups. This will incur an anti-drift penalty and reduce your score.

### Tip 3: Watch the Clock (Time Decay Multiplier)
* Each scenario gives you a generous time limit (e.g., 20 minutes).
* For the first 50% of the time, the time multiplier is **$1.0$ (100% score)**.
* If you take longer than 50% of the time, the score decays exponentially.
* **Pro-tip**: Read the scenario narrative quickly, run `t2t audit`, write your fix, and submit within 5–8 minutes for a guaranteed $>95$ score.

### Tip 4: Ask the Socratic Mentor for Clues, Not Answers
* Run `t2t hint`.
* The AI mentor will ask you targeted questions:
  * *"Check the route protocol for 10.10.99.0/24 on R3 using show ip route. Is it 'O E2' or 'D EX'?"*
  * *"What is the administrative distance of an OSPF external route versus an EIGRP external route?"*
* Think about the answer to that question, and the exact configuration command will become obvious.

---

## 3. Step-by-Step Hands-On Tutorial (Beginner Walkthrough)

Follow this 5-minute tutorial to master the workflow:

### Step 1: Check System Health
```bash
# Run the built-in end-to-end replay demo
t2t demo
```
* This exercises the environment doctor, loads fallback fixtures, and ensures your Python virtual environment is healthy.

### Step 2: Inject Scenario T3
```bash
t2t new-ticket --fault T3
```
* **Output**:
  ```
  Ticket T3-SUBOPTIMAL-01 initialized.
  Problem: Branch R1 reports high latency and intermittent packet drops reaching HQ 10.10.99.0/24.
  Target Routers: R2 (ASBR), R3 (ASBR)
  Time Limit: 20 minutes
  ```

### Step 3: Check Current Status & Failed Invariants
```bash
t2t status
```
* Notice that the invariant check `c_t3_r3_route` shows status **FAIL**:
  * Expected: `protocol=eigrp`
  * Observed: `protocol=ospf`
  * Message: *"R3: prefix 10.10.99.0/24 known via ospf, expected eigrp."*

### Step 4: Run Static Audit to Pinpoint the Defect
```bash
t2t audit
```
* Rule A5 flags: *"AD Inversion detected on R3: OSPF (110) preferred over EIGRP External (170)."*

### Step 5: Submit the Fix
```bash
t2t submit --replay -e "Configured distance ospf external 171 on R3 to ensure EIGRP external path is preferred."
```
* **Output**:
  ```
  ┏━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
  ┃ Check ID      ┃ Status ┃ Expected       ┃ Observed       ┃ Message                                ┃
  ┡━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
  │ c_t3_r3_route │  PASS  │ protocol=eigrp │ protocol=eigrp │ Route converged over optimal path.     │
  └───────────────┴────────┴────────────────┴───────────────┴────────────────────────────────────────┘
  
  All checks passed!
  Base Score: 100.0 | Time Decay: 0.985 | AST Drift Penalty: 0.0
  FINAL SCORE: 98.5 / 100 (Ticket RESOLVED)
  ```

### Step 6: View the Result in the Browser & Web Dashboard Demo
```bash
# Launch dashboard in offline replay mode
t2t web --replay --port 8000
```
* Open `http://127.0.0.1:8000` in Chrome/Edge/Firefox.
* The link between R3 and R1 is now bright green!
* The ticket history displays your 98.5 score and resolved timestamp.
* Open `http://127.0.0.1:8000/docs` to inspect interactive Swagger API documentation.
* Query REST endpoints via terminal:
  ```powershell
  curl http://127.0.0.1:8000/api/status
  curl http://127.0.0.1:8000/api/session
  curl http://127.0.0.1:8000/api/history
  curl http://127.0.0.1:8000/api/audit/latest
  ```

### Step 7: How to Abandon a Failed Ticket (Reset Back to Baseline)
If verification checks fail (e.g. `c_t3_r3_route FAIL`) or you want to restart/cancel a session without recording a score:
```bash
# Abandon active ticket and restore golden baseline
t2t abandon --replay -y
```
* **What it does**: Clears the active session lock in `.t2t/state.json`, resets the session FSM from `ACTIVE` back to `IDLE`, and restores all router configurations to the pristine baseline golden state.
* If you want to see the exact Cisco remediation commands that would solve the ticket:
  ```bash
  t2t reveal --replay -y
  ```

---

## 4. Common Pitfalls & How to Avoid Them

| Mistake | What Happens | The Correct Approach |
| :--- | :--- | :--- |
| **Forgetting `subnets` in OSPF** | Only classful networks (e.g. `10.0.0.0/8`) are redistributed. Subnets like `10.1.12.0/24` are lost. | Always use `redistribute eigrp <AS> subnets`. |
| **Forgetting EIGRP seed metric** | EIGRP assigns an infinite metric. Routes are silently discarded. | Configure `default-metric 10000 100 255 1 1500` or specify `metric` on the `redistribute` command. |
| **Using identical route tags on both ASBRs** | If R2 and R3 both tag routes with `100`, they will each deny each other's valid prefixes. | Use distinct tags: Tag with 110 on R2, Tag with 120 on R3. On R2 deny 120; on R3 deny 110. |
| **Missing the final permit in a route-map** | Cisco route-maps have an implicit `deny all` at the end. All routes get blocked. | Always add a blank permit sequence at the end (`route-map NAME permit 999`) if you only want to filter specific prefixes. |
| **Editing `README.md` instead of docs** | Breaks AGENTS.md project rules. | Document all student and presentation work in `docs/` and `README_NEW.md`. |

---

## 5. Troubleshooting & Frequently Asked Questions

### Q: Why do I get `FileNotFoundError: inventory.yaml`?
**Fix**: In Phase 9, we packaged fallback fixtures into `src/t2t/demo_data/`. Make sure you run `t2t demo` or provide `--replay` flag, which automatically uses the packaged fallback files.

### Q: Why does the web server refuse to bind to `0.0.0.0`?
**Fix**: By design, `t2t web` binds strictly to `127.0.0.1` for security. To bind to all interfaces (e.g., in a VM or container), you must supply both `--allow-remote` AND set `T2T_WEB_TOKEN`:
```bash
$env:T2T_WEB_TOKEN="secret123"
t2t web --host 0.0.0.0 --allow-remote --token secret123
```

### Q: How do I test the whole project after making changes?
**Fix**: Run our fast regression test suite:
```powershell
.\.venv\Scripts\python.exe -m pytest -v
```
All 129 tests should execute and pass in ~10 seconds.
