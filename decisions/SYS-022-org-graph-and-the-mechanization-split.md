# SYS-022: The fleet division of labor is this system's org graph — and a graph claim must name which half is mechanized

**Status:** Accepted
**Date:** 2026-08-09
**Deciders:** San Lee

---

## Context

Through 2026 the practitioner vocabulary for building on models acquired a fourth rung.
**Prompt engineering** (2023) governs one model response. **Context engineering** (mid-2025,
after Karpathy's framing) governs what fills the window. **Loop engineering** (2025 through
mid-2026) governs one agent's unattended observe-act-verify-recover cycle. **Graph
engineering** — the term crystallized publicly around July 2026 — governs how *many* agents
are organized: inter-agent routing, node failure isolation, state consistency across the work
graph, dynamic node spawning, and graph observability.

Two properties of that fourth rung matter here, and both come from the same body of writing:

1. **The layers stack; they do not replace.** A prompt does not disappear when a loop is built
   around it — it stops being the thing typed by hand.
2. **Production systems run two graphs, not one.** A stable **org graph** (roles, ownership,
   who may do what) and an ephemeral **work graph** (this task's decomposition, and the state
   flowing along its edges). The characteristic failure of the layer is that **context does not
   cross a node boundary unless an edge explicitly carries it.**

This system has a four-vendor fleet with typed roles and conditional escalation edges, recorded
in [agent-ops `ADR-010`](https://github.com/sanlee-ys/agent-ops/blob/main/decisions/ADR-010-claude-led-four-vendor-orchestration.md)
and amended by [`ADR-012`](https://github.com/sanlee-ys/agent-ops/blob/main/decisions/ADR-012-capability-parity-and-the-guard-obligation.md).
It has a dispatch room, `telltale council`, that routes turns across those vendors. It has
per-vendor guard hooks enforced at tool time. Asked plainly whether that constitutes graph
engineering, the tempting answer is yes, and the tempting answer is where the risk is.

**The risk is `SYS-019`'s, in a new place.** That decision's finding was that a surface which
*looks* like proof is not proof. Here the surface is a vocabulary: the fleet genuinely has the
shape the word describes, so the word fits well enough that nobody checks which parts of it are
actually built. An unqualified "this system does graph engineering" is a claim about a runtime
that does not exist, made on the strength of a policy document that does.

The distinction is not academic, because the two halves fail differently. An org graph fails by
**ambiguity** — nobody knows who owns a node, and the same work gets done twice or not at all.
A work graph fails by **silent context loss** at a handoff. Only the first failure mode is one
this system has instrumentation for.

## Decision

**The four-vendor division of labor is this system's org graph, recorded and governed as one.
No work-graph runtime exists. Any claim that this system practices graph engineering must
state which graph-harness concerns are mechanized and which are hand-executed; the unqualified
claim is not available.**

The normative content is the split. Measured against the five concerns a graph harness is
said to manage, as of 2026-08-09:

| Concern | Instrument | Mechanized? |
|---|---|---|
| Inter-agent message routing | `telltale council` — default route to the control plane, `@codex`/`@agy`/`@cursor` route a single turn, `+@`/`-@` set operations, and the route is priced in the composer before send ([`docs/council.md`](https://github.com/sanlee-ys/telltale/blob/main/docs/council.md), *Routing: who a turn actually reaches*) | **Yes** — real code |
| Graph observability | The same room: turn view, focus rail, seat badges, live band | **Yes** — real code |
| Node failure isolation | Per-vendor guard hooks wired at tool time on all four vendors (`ADR-012`); `/arena` worktree containment | **Partial** — this is node *containment and policy*, which is adjacent to failure isolation, not identical to it |
| State consistency | One `room.json` per room, and concurrent councils are **last-save-wins** by the room's own admission. Cross-vendor transfer is a hand-carried frozen brief plus a pushed branch or revision | **Weak** |
| Dynamic node spawning | The seat roster is fixed at four. Spawning happens *inside* the Claude node, via subagents and worktrees | **No**, at the graph layer |

Three consequences of that table are binding:

1. **Conversational routing is not work routing.** `telltale council` routes *who hears this
   turn*. It does not decompose a task into owned nodes, and nothing in it assigns, tracks, or
   reconciles node ownership. The two look identical in a terminal and are different layers.
   A claim that reads the first as the second is wrong, not imprecise.
2. **The edge contracts are prose, and prose is the mechanism.** The fleet's rule that only
   inspectable state crosses a vendor boundary — a frozen brief, an explicit file boundary, a
   pushed branch or exact revision, verification already run — exists precisely because no
   runtime carries state along an edge. It is a hand-built solution to the layer's
   characteristic failure, and it is enforced by an agent reading it, which means its failure
   rate is not zero. See [agent-ops `vendors/`](https://github.com/sanlee-ys/agent-ops/blob/main/vendors/README.md)
   for the public harness contracts.
3. **Adopting a graph framework is a separate decision, not an increment.** Wiring a
   `StateGraph`-style runtime (LangGraph, AutoGen GraphFlow, Google ADK, CrewAI) would supply
   rows 3 through 5 and would also relocate the routing and observability this system already
   owns. That is a replacement of working surfaces, and it needs its own record with its own
   alternatives — it is not a fast-follow to this one.

**On why this is not `SYS-019`-grade enforcement.** `SYS-019` says a claim with a
machine-readable source of truth must be asserted mechanically, and that a human-read list is
the weakest instrument. This decision cannot meet that bar and does not pretend to: there is no
artifact whose staleness a build could compare a *vocabulary* claim against. What it does
instead is the `SYS-021` move — fix the honest statement at the one moment it is cheaply
checkable (when the claim is written), and say plainly that continuous assurance is not
provided. Naming the bound is the point.

## Downstream surfaces

- **[agent-ops `ADR-010`](https://github.com/sanlee-ys/agent-ops/blob/main/decisions/ADR-010-claude-led-four-vendor-orchestration.md)
  and [`ADR-012`](https://github.com/sanlee-ys/agent-ops/blob/main/decisions/ADR-012-capability-parity-and-the-guard-obligation.md)**
  — the org graph's actual specification: typed nodes, and edges with trigger predicates
  (Codex after two failed hypothesis-driven attempts or visible looping; Antigravity as a third
  opinion when Claude and Codex disagree). **Not edited here.** This decision classifies them;
  it does not restate their content, deliberately, so it is not itself an unverified claim
  about a surface it did not touch.
- **[agent-ops `vendors/`](https://github.com/sanlee-ys/agent-ops/blob/main/vendors/README.md)**
  — the public harness contracts, and the natural home for an edge-contract section if the
  prose rule is ever promoted to something checkable.
- **`telltale` (`docs/council.md`, `README.md`)** — the room is this system's routing and
  observability layer whether or not it is described that way. If its README ever reaches for
  the graph vocabulary, requirement 1 above governs the wording. **Not edited here.**
- **[`SYS-019`](SYS-019-assert-claims-dont-list-them.md)** — parent finding; complementary, not
  superseded. See the enforcement note above.
- **[`SYS-021`](SYS-021-agentic-ci-proves-itself-by-artifact.md)** — the same shape one layer
  down: a green harness is not evidence the work happened, and a fitting vocabulary is not
  evidence the runtime exists.
- **[`SYS-016`](SYS-016-agent-tool-seam-threat-model.md)** — the guard hooks counted in row 3
  are that threat model's instrument. Counting them as graph-layer node policy is a
  reclassification, not a new control.
- **[`SYS-003`](SYS-003-agent-tool-layer-contract.md)** — the tool seam is an edge in the org
  graph, and the only one with a frozen wire shape.
- **[`ADR-001`](../adr/ADR-001-documentation-portal.md)** — its Phase 2 system map renders repos
  and tool seams. That is a picture of a *different* graph (repo topology), and should not be
  conflated with the org graph recorded here.
- **Portfolio and public writeups** — any surface claiming this system does graph engineering
  is bound by the Decision. Unqualified use is the failure this record exists to prevent.

## Consequences

- **What this makes easier.** Talking about the fleet precisely, in public, without either
  overclaiming a runtime or underselling an org graph that genuinely exists and is genuinely
  governed. It also makes the missing pieces legible as a list rather than a vibe.
- **What it costs.** Every use of the term now carries a qualifying clause. That is more
  friction than "we do graph engineering," and the friction is the deliverable.
- **What it forecloses.** Three things: the unqualified claim; reading `telltale`'s
  conversational routing as work routing; and treating framework adoption as the way to *become*
  graph-engineered rather than as a separate, alternatives-bearing decision.
- **A known, accepted hole.** Nothing checks this. The claim discipline is enforced by a human
  or an agent reading this record before writing the sentence, which is the instrument
  `SYS-019` rates weakest. It is the strongest one available for a claim with no artifact
  behind it, and calling that out is more useful than a check that would pass on silence.
- **A second hole, named rather than fixed.** The table is a point-in-time measurement. Rows
  can change without anything failing — `telltale` could gain node-level retry, or the roster
  could stop being fixed at four — and the table would go stale silently. The trigger below is
  the mitigation, and it is a weaker one than a build step.
- **Revisit when** any of: a work-graph runtime is adopted; the seat roster stops being fixed;
  cross-vendor state transfer stops being hand-carried; or a public surface needs the
  unqualified claim badly enough to argue for it.

## Alternatives Considered

| Option | Reason Not Chosen |
|--------|-------------------|
| **Say yes — the DoL is graph engineering, full stop** | It is the flattering answer and it is wrong on two of five rows, weak on a third. It claims a runtime that does not exist on the strength of a policy document that does, which is `SYS-019`'s exact failure with a new noun. |
| **Say no — this is just a documented division of labor** | Equally wrong, in the other direction, and it discards the harder half. Typed nodes, conditional escalation edges, and mechanically-enforced per-node policy are the org graph, and per the source material the org graph is the stable half most teams skip on the way to work-graph plumbing they then cannot govern. Denying it would be false modesty that also loses the sequencing insight. |
| **Skip the record; adopt LangGraph and make the claim true** | Inverts the order. It buys rows 3–5 by replacing rows 1–2, which are working, and it does so before the edge contracts that would define the node boundaries are anything but prose. A runtime routing state between under-specified nodes is a faster way to lose context, not a slower one. Kept as a real future option, gated behind its own decision. |
| **Record it as a repo-local `ADR` in `adr/`** | Fails the first prong of `SYS-001`'s promotion bar in reverse: the claim it governs is made in `agent-ops`, `telltale`, and public portfolio copy, none of which read this repo's local tier. A rule about what other repos may assert has to live in the system log. |
| **Fold it into `SYS-019` as an amendment** | `SYS-019` is about claims with a machine-readable source of truth, and its whole force is that such claims must be asserted mechanically. This claim has no artifact and cannot be. Amending it here would blur the one distinction that gives `SYS-019` its teeth. |
| **Wait until the split changes, then record once** | This is the version that never gets written. The measurement is cheap today because the surfaces were read today; in three months the table would be reconstructed from memory, which is how three surfaces ended up citing a wrong number in the 2026-07-18 audit. |
