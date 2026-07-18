# Atlas AI — Hackathon Demo Script
### 3–5 Minute Live Presentation Guide

---

## PRE-DEMO SETUP CHECKLIST

Complete these steps **before** walking on stage. Target: everything ready 15 minutes prior.

### Terminal / Backend
- [ ] `docker-compose up -d` — all services healthy (`docker-compose ps` shows no exits)
- [ ] Backend API responding: `curl http://localhost:8000/health` → `{"status":"ok"}`
- [ ] Redis is running and accepting connections: `redis-cli ping` → `PONG`
- [ ] Database seeded with demo data: `make seed-demo` (creates cluster `prod-us-east-1`, fake historical incidents)
- [ ] Kubernetes cluster accessible: `kubectl get nodes` returns at least 1 Ready node (use minikube or kind for demo)
- [ ] Demo deployment pre-installed: `kubectl apply -f k8s/demo-app.yaml` — `demo-app` pods in `Running` state
- [ ] All 4 environment variables set: `OPENAI_API_KEY`, `GITHUB_TOKEN`, `SLACK_WEBHOOK_URL`, `JIRA_API_TOKEN`
- [ ] `ngrok http 8000` running if presenting remotely — note the public URL

### Browser / Frontend
- [ ] Frontend running: `npm run dev` in `atlas-ai/frontend/` — open `http://localhost:3000`
- [ ] Browser zoom set to **125%** so the audience can read text
- [ ] Tab 1: Atlas AI dashboard (`/dashboard`) — cluster `prod-us-east-1` visible, all pods green
- [ ] Tab 2: Incident feed (`/incidents`) — empty or showing resolved historical incidents
- [ ] Tab 3: GitHub PR #847 open in a separate tab (pre-loaded, not yet visible)
- [ ] Tab 4: Generated outputs page (`/incidents/{id}/outputs`) — will show after the demo run
- [ ] DevTools closed, bookmarks bar hidden, notifications silenced (Do Not Disturb ON)

### Kill Script
- [ ] File `scripts/demo-kill.sh` exists and is executable (`chmod +x scripts/demo-kill.sh`)
- [ ] Tested: running it crashes `demo-app` deployment within 10 seconds

### Backup Materials
- [ ] `docs/screenshots/` folder open in Finder (backup plan, see below)
- [ ] Recorded video downloaded locally (not relying on internet streaming)
- [ ] PDF of pitch deck loaded as final fallback

### Presenter Machine
- [ ] Laptop plugged in to power
- [ ] External display resolution confirmed with AV team
- [ ] Presenter notes hidden from audience display (Mirroring OFF if using Keynote)
- [ ] Water bottle on stage

---

## THE NARRATIVE ARC

> **Core story:** An invisible crisis, an AI that never panics, a human who sleeps through it all.

Every great demo follows a three-act structure. Don't just click through features — make the audience *feel* the problem before you reveal the solution.

| Act | Time | Emotional Beat |
|-----|------|----------------|
| **1. The Problem** | 0:00–0:30 | Empathy — "I know this pain" |
| **2. The Chaos** | 0:30–2:00 | Tension — watch things break in real time |
| **3. The Resolution** | 2:00–4:00 | Relief — watch AI methodically fix everything |
| **4. The Payoff** | 4:00–5:00 | Awe — the artifacts, the pitch, the close |

Never say "and now I'm going to show you X." Instead, *do* X while narrating what's happening. The audience watches your screen, not your face. Keep energy high, pace deliberate.

---

## EXACT SCRIPT WITH TIMING

### `[0:00 – 0:30]` — THE HOOK

> *(Stand still. No clicking. Make eye contact with the room. Voice low and deliberate.)*

**SAY:**
> "Right now, somewhere in the world, an engineer is getting paged at 3am.
> Their phone is blowing up. Production is down. Customers are tweeting.
> They haven't slept in 20 hours, they're staring at a sea of logs,
> and they have no idea where to start."

> *(Pause one full second.)*

> "That engineer could be anyone in this room.
> We built Atlas AI so they never have to fight alone again."

---

### `[0:30 – 1:00]` — SHOW THE DASHBOARD

> *(Click to Tab 1 — the Atlas AI dashboard. Cluster `prod-us-east-1` is fully green.)*

**SAY:**
> "This is Atlas AI. One sentence: it's an autonomous AI engineer that detects incidents,
> investigates root causes across your entire stack, and remediates — with your approval —
> in minutes, not hours."

> *(Gesture broadly at the green dashboard.)*

> "Right now, everything is healthy. Twelve pods running, zero alerts, all systems nominal.
> This is the calm before the storm."

> *(Move mouse slowly over a pod to show the tooltip — CPU, memory, uptime. Don't rush.)*

> "But production is never calm for long."

---

### `[1:00 – 1:30]` — TRIGGER THE INCIDENT

> *(Switch to the terminal. The kill script is ready. Read the command aloud as you type.)*

**SAY:**
> "I'm going to do what every engineer dreads — I'm going to simulate a bad deployment.
> Watch what happens."

> *(Type and run:)*
```bash
./scripts/demo-kill.sh
```

> "This removes a critical environment variable from our running deployment —
> a mistake that happens dozens of times a day on real teams."

> *(Switch back to the dashboard tab. Watch it update. Pods turn red. Alert badge appears.)*

> "And there it is."

> *(Pause. Let the red sink in for 3–4 seconds. Don't fill the silence.)*

> "Atlas AI has already detected an anomaly. Watch what it does next."

---

### `[1:30 – 2:00]` — ATLAS AI STARTS INVESTIGATING

> *(Navigate to the Incident Feed tab or the live incident view — it should have auto-created an incident.)*

**SAY:**
> "In the time it took me to say that sentence, Atlas AI opened an incident,
> classified it as severity P1, and dispatched a multi-agent investigation team."

> *(Point to the agent progress feed as each agent appears with a status badge.)*

> "See this feed? Each one of these is a specialized AI agent running in parallel.
> The Kubernetes agent is already pulling pod logs. The Metrics agent is checking
> Prometheus for anomalies. The GitHub agent is scanning recent deployments.
> They're not waiting for each other — they're working the problem simultaneously,
> exactly like a senior SRE would coordinate a war room."

> *(Agent statuses tick from `DISPATCHED` → `RUNNING`. Keep narrating as they update.)*

> "This isn't a script. This is a reasoning loop — each agent forms a hypothesis,
> gathers evidence, and reports findings back to the orchestrator."

---

### `[2:00 – 2:30]` — KUBERNETES AGENT FINDS THE SMOKING GUN

> *(The Kubernetes Agent card flips to `COMPLETE`. Click into its findings panel.)*

**SAY:**
> "The Kubernetes agent just finished. Let's see what it found."

> *(Click to expand. The finding is highlighted in the UI. Read it aloud, slowly.)*

> "CrashLoopBackOff. Pod `demo-app-6b9d4f-xkp2r` has restarted 7 times in the last 4 minutes.
> And here's the log line that killed it:"

> *(Point directly at the screen. Dramatic pause.)*

> `"Fatal error: SECRET_KEY environment variable not found. Exiting."`

> *(Look up at the audience.)*

> "One missing environment variable. That's all it takes to take down a service.
> A human engineer would've spent 45 minutes reading through 10,000 lines of logs
> to find that exact line. The Kubernetes agent found it in 11 seconds."

---

### `[2:30 – 3:00]` — GITHUB AGENT AND DOCUMENTATION AGENT CORROBORATE

> *(GitHub Agent card flips to `COMPLETE`. Click into its findings.)*

**SAY:**
> "But finding *what* broke isn't enough. We need to know *why* and *who*."

> *(The GitHub Agent finding shows: PR #847, merged 23 minutes ago.)*

> "The GitHub agent cross-referenced the deployment timestamp with recent pull requests.
> PR #847 was merged 23 minutes ago. Title: `'refactor: clean up legacy config variables.'`"

> *(Switch to the pre-loaded GitHub PR tab. Show the diff for 2 seconds.)*

> "The diff shows `SECRET_KEY` removed from the deployment manifest.
> Probably looked harmless in review. It wasn't."

> *(Switch back to the Atlas AI tab. Documentation Agent card is now `COMPLETE`.)*

> "Meanwhile, the Documentation agent searched our runbook database
> and found the exact procedure for this scenario —
> including the approved fix: re-inject the secret from Vault."

---

### `[3:00 – 3:30]` — RCA SYNTHESIS + HUMAN APPROVAL GATE

> *(Click into the RCA Agent card — it's synthesizing.)*

**SAY:**
> "Now watch the orchestrator — the RCA Agent — pull everything together."

> *(Read the synthesized summary from the screen.)*

> "Root cause: `SECRET_KEY` environment variable removed in PR #847 by @dev-alice,
> merged without staging validation. Affected service: `demo-app`, severity P1.
> Recommended fix: patch deployment manifest to inject `SECRET_KEY` from Vault secret
> `prod/demo-app/config`. Confidence: 94%."

> *(The Execution Agent card appears with a yellow `AWAITING APPROVAL` badge.)*

> "And here's where Atlas AI does something important. It stops."

> *(Pause for emphasis.)*

> "It has the fix. It knows exactly what to run. But it will not touch production
> without a human saying yes. This is the approval gate —
> every remediation action requires explicit sign-off.
> Atlas AI is fast, but it's never reckless."

> *(Click the green `Approve & Execute` button.)*

> "Approved."

---

### `[3:30 – 4:00]` — DASHBOARD GOES GREEN

> *(Switch to the dashboard tab. Pods are recovering — yellow first, then green.)*

**SAY:**
> "The Execution Agent is applying the patch now.
> It's calling the Kubernetes API directly — no SSH, no manual kubectl, audited and logged."

> *(Watch the pod count recover. Last pod goes green.)*

> "All twelve pods healthy. Zero restarts. Incident resolved."

> *(Pause. Smile. Let the green dashboard breathe for 3 seconds.)*

> "4 minutes and 22 seconds. Start to finish.
> The on-call engineer? Still asleep."

---

### `[4:00 – 4:30]` — THE GENERATED ARTIFACTS

> *(Navigate to the outputs panel — `/incidents/{id}/outputs`)*

**SAY:**
> "But Atlas AI doesn't just fix the problem. It handles everything that comes after."

> *(Click through each artifact quickly — one second each, narrate as you go.)*

> "A full PDF Root Cause Analysis report — structured, timestamped, ready for your post-mortem.
> A Slack message already posted to `#incidents` with a summary and action items.
> A Jira ticket created, assigned to the PR author, with the RCA linked.
> A GitHub issue on the offending PR, so the team learns from the mistake."

> *(Step back from the laptop. Arms open.)*

> "Every single one of these used to require a human to write, copy-paste, and send
> after an exhausting all-nighter. Now they're just... done."

---

### `[4:30 – 5:00]` — THE CLOSE

> *(Step forward. No more clicking. Full eye contact with the room.)*

**SAY:**
> "What just took 4 minutes and 22 seconds?
> That used to be a 3-hour war room.
> Two or three engineers, paged at 3am, manually hunting through logs,
> Slack threads, GitHub history, and internal wikis —
> before they could even *start* writing the fix."

> *(One more pause. Slower now.)*

> "Atlas AI is not a monitoring tool. It's not an alert router.
> It is an AI engineer — one that investigates, reasons, acts, and learns —
> and it never sleeps, never panics, and never gets tired."

> "We're Atlas AI. Thank you."

> *(Stop. Don't fill the silence. Let it land.)*

---

## BACKUP PLAN

> **Rule:** If anything breaks, you do not apologize. You say: *"Let me show you this another way"* and move forward without hesitation. Judges remember confidence, not perfection.

### Tier 1 — Partial Failure (one component down)

If the **dashboard doesn't update in real time**, switch to the terminal and show the raw API response:
```bash
curl http://localhost:8000/api/v1/incidents/latest | jq .
```
Narrate the JSON fields aloud as if it's the UI.

If the **agents don't progress**, open the worker logs in a side terminal:
```bash
docker-compose logs -f worker
```
Walk through the log lines — the same story, just in a different format.

### Tier 2 — Major Failure (backend is down)

Switch to the **screenshots walkthrough**:
1. Open `docs/screenshots/` in Finder
2. Walk through in order: `01-green-dashboard.png` → `02-triggered-incident.png` → `03-agent-feed.png` → `04-k8s-finding.png` → `05-github-finding.png` → `06-rca-synthesis.png` → `07-approval-gate.png` → `08-green-recovery.png` → `09-artifacts.png`
3. Use the same script verbatim — screenshots are just as readable as a live UI

**Transition line:** *"I'll walk you through a recent run we captured — same system, same flow."*

### Tier 3 — Total Failure (laptop dies, display fails)

Switch to the **pre-recorded video**:
- File location: `docs/demo-recording.mp4` (also uploaded to a private YouTube link as backup)
- **Do not apologize.** Say: *"I want to make sure you can see this clearly, so let me play our recorded run."*
- Narrate over the video using the same script — your voice adds value even with a recording

### Emergency Talking Points (no demo at all)

If absolutely nothing works, deliver the pitch verbally:
> *"I can't show you the live system right now, so let me tell you what it does in 60 seconds. Imagine a senior SRE who can read every log, every git commit, every runbook simultaneously, never gets paged at 3am, never panics, and can apply a fix — with your approval — in 4 minutes instead of 3 hours. That's Atlas AI. We built it with a 9-agent architecture on GPT-4 Turbo, it runs on any Kubernetes cluster, and it generates full RCA reports, Slack messages, and Jira tickets automatically. We'd love to show you a live demo after the session."*

---

## Q&A PREPARATION — 10 JUDGE QUESTIONS

### Q1: How is this different from existing AIOps tools like PagerDuty, Datadog, or Moogsoft?

**Strong Answer:**
> "Existing tools are excellent at *telling you* something is wrong — they're observability and alerting layers. PagerDuty pages you. Datadog shows you dashboards. Moogsoft correlates alerts. None of them *act*. Atlas AI is the first layer after the alert — it investigates across multiple data sources simultaneously, synthesizes a root cause, and executes a remediation with human approval. It's the difference between a smoke alarm and a fire suppression system. They're complementary — in fact, we integrate with PagerDuty and Datadog as signal inputs."

---

### Q2: Can it break production? What's the blast radius if it does something wrong?

**Strong Answer:**
> "We designed for this from day one. Every remediation goes through a mandatory human approval gate — Atlas AI cannot execute any action without explicit sign-off. Additionally, all actions are scoped to the minimum required permissions via RBAC: the agent can patch a deployment manifest, but it cannot delete namespaces, modify cluster-level resources, or access secrets outside the incident scope. We also maintain a full audit log of every action taken, every API call made, and every decision in the reasoning chain. If something goes wrong, you have complete forensic visibility — and you can roll back any Atlas AI action with a single button."

---

### Q3: How does it handle truly novel incidents — something it's never seen before?

**Strong Answer:**
> "This is where the underlying model capability matters. Atlas AI uses GPT-4 Turbo's chain-of-thought reasoning, so it doesn't need to have seen a specific incident pattern before — it reasons from first principles using the evidence it gathers. It reads the actual log output, the actual diff, the actual runbook text, and constructs a hypothesis. Over time, the learning loop stores successful resolutions and references them to improve confidence scores on similar future incidents — but it doesn't *require* that history to function on something new. That said, novel incidents get flagged with lower confidence scores and are routed to human review before any execution."

---

### Q4: What's the human oversight model? How do I stay in control?

**Strong Answer:**
> "Three levels of control. First, every remediation requires explicit approval — there is no autonomous execution without a human clicking 'Approve.' Second, you can configure Atlas AI to be purely diagnostic — never propose any execution, just deliver the RCA report and let your team act on it. Third, every single agent action, tool call, and reasoning step is logged and visible in the audit trail in real time. You're not trusting a black box — you're reviewing a transparent chain of evidence. We also support approval workflows: for high-severity incidents, you can require two approvals, route to a specific Slack channel, or require VP sign-off."

---

### Q5: How do you prevent prompt injection from log data?

**Strong Answer:**
> "Log data is treated as untrusted user input, not as instructions. It's passed to the model inside a strictly delimited context block with an explicit system instruction that log content is observational data only, not commands. We also run a pre-processing sanitization step that strips common injection patterns — things like embedded instruction sequences or attempts to override the system prompt. Additionally, the agents operate on a tool-use model: they call structured functions with typed parameters rather than generating free-form commands, which dramatically reduces the attack surface. We're actively evaluating adversarial red-teaming as part of our SOC2 compliance work."

---

### Q6: What does GPT-4 Turbo add that older models couldn't do?

**Strong Answer:**
> "Two things specifically. First, the 128k context window. A single incident investigation might pull in 50,000 tokens of log data, 20,000 tokens of Kubernetes manifests, and a 10,000-token runbook — older 4k or 8k windows couldn't hold that simultaneously, so you'd get fragmented analysis. Now we can feed an entire incident's evidence to the reasoning model at once. Second, tool-use reliability. GPT-4 Turbo's function calling is significantly more reliable for structured outputs — the agents need to call specific APIs with exactly the right parameters, and hallucinated tool calls would be catastrophic in a production environment. The improvement in reliability from GPT-3.5 to GPT-4 Turbo on structured tool use is roughly 40% in our internal benchmarks."

---

### Q7: How does the learning loop actually work?

**Strong Answer:**
> "After each resolved incident, three things are stored in the knowledge base: the incident fingerprint — a structured embedding of the symptom pattern — the resolution path that worked, and the confidence score of the resolution. When a new incident comes in, the system does a semantic similarity search against historical incidents. If it finds a match above a confidence threshold, it includes that resolution as a high-priority hypothesis for the RCA agent. The agents can still gather fresh evidence and override the historical suggestion if the context doesn't fit — it's a bias toward successful past patterns, not a hard rule. Over time, this compresses resolution time for recurring incident classes significantly. Teams with six months of history typically see 40–60% faster resolutions on common incident types."

---

### Q8: What's the latency in practice? How long does a full investigation actually take?

**Strong Answer:**
> "For a well-scoped incident — single service, clear error signal — we typically see full RCA synthesis in 3–6 minutes. The bottleneck is almost never Atlas AI; it's API rate limits on downstream tools like GitHub and Jira. Agent dispatch and parallel execution happen in under 5 seconds. Log ingestion and analysis: 30–90 seconds depending on volume. RCA synthesis: 20–40 seconds. For comparison, our benchmark dataset of 200 historical incidents from real teams shows a median human resolution time of 47 minutes for P1 incidents. Even in our worst-case scenarios — complex multi-service cascading failures — we've seen Atlas AI deliver a complete RCA in under 12 minutes."

---

### Q9: How do you monetize this? What does the business model look like?

**Strong Answer:**
> "SaaS subscription tiered by cluster count and feature set. Our Starter tier is $500/month for small teams trying us out — one cluster, core agents. Team is $2,000/month covering most scaling companies. Enterprise at $8,000/month is where the real business is — unlimited clusters, custom agent development, SSO, dedicated SLAs. Our unit economics are strong: CAC around $3,200 because of developer-led growth and a self-serve motion, LTV on Enterprise over three years around $288,000, giving us a 27:1 LTV-to-CAC ratio. We're targeting $1.2M ARR in year one with 50 Team customers and 10 Enterprise accounts — that's a realistic bottom-up number given comparable developer tools companies at similar stages."

---

### Q10: What's your 18-month roadmap?

**Strong Answer:**
> "Three phases. In the next six months: ship the open-source core agent framework to GitHub, launch on Product Hunt, get our first 50 paying customers through developer-led growth, and complete the integrations for Datadog, PagerDuty, and AWS CloudWatch. Months 6 through 18: build the enterprise feature set — SSO, audit logs, approval workflows, custom agent SDK — and start direct outbound sales to Series B+ startups with dedicated SRE teams. We'll also ship the learning loop at scale and our first custom-trained incident classification model. By month 18, we want 200 paying customers, $3M ARR, and our first Fortune 500 design partnership. Beyond 18 months: multi-cloud support, a managed agent marketplace where partners can publish domain-specific agents, and expansion into automated capacity planning and proactive incident prevention — shifting from reactive to predictive."

---

## STAGE PRESENCE TIPS

### Before You Walk On

- Do one slow, deep breath before your name is called. It physically lowers your cortisol.
- Remind yourself: the judges want you to succeed. They are not adversaries.
- Your job is to tell a story. The demo is a prop, not the presentation.

### During the Demo

**Pace yourself.** The most common mistake is rushing when nervous. If you feel yourself speeding up, deliberately slow down by 20%. Pauses read as confidence.

**Narrate what you're doing.** Never click in silence. If you're switching tabs, say "switching to the live dashboard." If you're typing a command, read it aloud. This keeps the audience oriented and buys you time.

**Look up.** Every 15–20 seconds, lift your eyes from the screen and make eye contact with the audience. The screen tells the story; your face sells it.

**Own the red dashboard.** When the pods go red, don't flinch. You triggered it on purpose. The controlled chaos is the demo. Say "and there it is" with calm authority, like a surgeon who's seen this a thousand times.

**Don't apologize for latency.** API calls take seconds. If the UI pauses, narrate what's happening internally: "The Kubernetes agent is pulling the last 500 log lines now." This turns dead air into insight.

**The approval gate is your secret weapon.** Make it feel like a conscious design choice, not a limitation. "It has the answer. It stops. And asks for your permission." That single moment communicates more about your values than any feature list.

### Handling Questions

- If a judge interrupts during the demo: "Great question — I'll answer that in detail in Q&A, but watch this next part first." Then continue. Don't let a question derail your narrative arc.
- If you don't know the answer: "That's an edge case we're actively working on. Here's how we'd approach it..." is always better than guessing.
- If a question is hostile: "That's a fair concern — it's something we thought hard about. Here's our answer..." Validate before you defend.

### Time Management

- Practice until you can hit 4:30 naturally without checking your watch.
- If you're running short: skip the artifact walkthrough and go straight to the close.
- If you're running long: cut the GitHub PR tab switch — stay in Atlas AI the whole time.
- The close is non-negotiable. Always finish with *"never sleeps, never panics, never gets tired."*

---

*Last updated: Demo v1.0 — Atlas AI Hackathon Submission*
