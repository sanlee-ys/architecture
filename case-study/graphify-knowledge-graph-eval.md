# Case Study — Evaluating graphify as a Cross-Repo Knowledge Graph

**Status:** Draft
**Date:** 2026-07-03
**Author:** San Lee

Credit up front: this case study evaluates [**graphify**](https://github.com/safishamsi/graphify)
by [safishamsi](https://github.com/safishamsi) (MIT license) — a Claude Code / Codex / Cursor
skill that turns a folder of code, docs, and other artifacts into a queryable knowledge graph.
Everything below is my evaluation of someone else's tool against this system's actual repos, not
a claim of originality on the underlying technique.

## The problem

Across my project repos — [architecture](..), `notes-api`, `defense-news-classifier`, `kb-agent`,
`learning-notes`, `portfolio`, `sanlee-ys`, `dotfiles` — the cross-repo relationships — which ADR
references which, which service calls which contract — lived only in my head and in whatever an AI
assistant could re-derive by grepping each session. That doesn't scale, and it's not reusable
across sessions.

## What graphify does

A three-pass pipeline, described in its own docs:

1. **Code structure (free, no API calls).** Tree-sitter parses classes, functions, imports, and
   call graphs locally. 25 languages supported.
2. **Video/audio (local, no API calls).** faster-whisper transcription, seeded with the code
   graph's top concepts to focus the transcript.
3. **Docs, papers, images (Claude subagents, costs tokens).** Parallel subagents extract nodes and
   edges from markdown/PDFs/images; code files are excluded from this pass entirely when the
   corpus is code-only.

Community detection runs the **Leiden algorithm** directly on the extracted graph — no embeddings,
no vector database. Every edge is tagged `EXTRACTED` (found directly in source), `INFERRED` (a
reasoned LLM guess, with a numeric confidence rubric), or `AMBIGUOUS` (flagged for review). That
confidence tagging is the detail that made me trust the output enough to act on it — it doesn't
present a guess with the same weight as a parsed import statement.

## Methodology

1. **Read the source before running it.** Pulled `ARCHITECTURE.md`, `SECURITY.md`, and the
   relevant modules (`detect.py`, `hooks.py`, `serve.py`) via the GitHub API before installing
   anything, to check what it actually does versus what the README claims.
2. **Single-repo pilot** on this `architecture` repo (3 code files, 23 ADR/doc files) before
   scaling to the full corpus.
3. **Scale to my full repo set**, each extracted and merged into one cross-repo graph
   (`graphify extract <repo> --global --as <tag>`), then re-clustered as a whole.
4. **Wire it into daily use**: an MCP server registered globally so an AI assistant can query the
   graph directly, and git hooks so each repo's structural layer stays current.

## What worked

**The ADR dependency graph came back exactly right, for $0.29.** The semantic pass over this
repo's 23 decision docs correctly reconstructed the full `SYS-NNN` reference chain — `SYS-004`
depends on `SYS-002` and `SYS-003`, `SYS-011` depends on `SYS-008`, and so on — as `EXTRACTED`
edges pulled straight from the markdown, not inferred. That's the exact "stop re-deriving this by
grep every session" payoff I was looking for.

> **Footnote added 2026-07-18, not a correction.** `SYS-008` and `SYS-011` have since been
> re-tiered to [`architecture/ADR-001`](../adr/ADR-001-documentation-portal.md) and
> [`ADR-002`](../adr/ADR-002-generated-roadmap-dashboard.md); the numbers are retired and
> tombstoned. The sentence above is **left exactly as written**, because it is a dated record
> of what an extractor found on the day it ran — a result, not an index. Rewriting a published
> measurement so it matches a later reorganisation would falsify the very thing this page
> exists to document, and would quietly turn "$0.29 bought a correct graph" into an unverifiable
> claim. `SYS-001`'s narrowed retroactivity rule says this explicitly: published results that
> name a document are footnoted, never rewritten.

**Community detection produced real, not cosmetic, groupings.** On the single-repo run, Leiden
split the corpus into distinctions I hadn't explicitly drawn but that were true in the docs — "AI
Services Architecture" (the three service repos + their HTTP contracts) came out as a separate
community from "Agentic Engineering Strategy" (how AI is used to build them). It also grouped all
eleven `SYS-NNN` decisions into one hyperedge at 0.98 confidence, and the three cross-service HTTP
contracts (`SYS-004`/`005`/`006`) into another at 0.97, unprompted.

**The "Knowledge Gaps" section found a real gap.** It flagged `SYS-010` (Security Posture) as
weakly connected — ≤1 edge, versus a dozen-plus for `SYS-002`/`SYS-003`. That's a legitimate
signal about which decisions are under-integrated into the rest of the docs, not a false positive.

**Security posture held up to inspection, not just to the README's claims.** `SECURITY.md` states
the tool makes no network calls during graph analysis — the only outbound call in the whole
pipeline is the semantic-extraction LLM call itself. I verified this by grepping `serve.py`,
`export.py`, `ingest.py`, and `global_graph.py` for telemetry/analytics/upload patterns; found
none. The MCP server is stdio-only (no network listener), and nothing is pushed to git — output
is 100% local to `graphify-out/` per repo or `~/.graphify/global-graph.json`. That matters for any
tool run against a full local dev environment, not just an isolated public repo — the risk surface
reduces to "is this content OK to send through the Anthropic API," which is the same bar normal use
already clears.

## What didn't work cleanly

**It doesn't distinguish your code from vendored code.** The first single-repo run produced 2,750
nodes and 177 communities — wildly inflated. The cause: a vendored, minified JS file
(`portal_src/javascripts/vendor/mermaid.min.js`) got parsed like first-party code, and its
obfuscated single- and two-letter function names (`MU()`, `e7()`, `OU()`) became 2,690 of the
2,707 "code" nodes. graphify does respect `.gitignore` and supports `--exclude` /
`.graphifyignore`, but has no default heuristic for "this is a vendored/minified dependency, not
your code" — that's on the operator to configure. Excluding the vendor path dropped the graph to
its real size: 64 nodes, 174 edges, 9 communities.

**The whole-system graph is honestly fragmented, not unified.** Merging my full repo set produced
1,309 nodes and **83 communities**, most with cohesion scores of 0.05–0.20 (low). The report
itself surfaced this honestly — 125 isolated nodes, 28 thin communities omitted. That's the
correct outcome, not a tool failure: these repos genuinely are mostly independent, and a graph
that invented false unity would be worse than one that says so. The real cross-repo signal is
narrower than the full graph suggests — e.g. Community 44 ("Cross-Project Tool Calls") correctly
isolated the `kb-agent` → `defense-news-classifier` HTTP integration boundary, which is the kind of
finding worth having, buried among many single-repo communities that aren't.

**The merged graph doesn't stay current automatically.** `graphify hook install` (installed across
my repos) rebuilds each repo's own `graphify-out/` on commit — AST layer only, no LLM cost. It does
**not** re-merge into `~/.graphify/global-graph.json` or re-run the semantic pass on changed docs.
Keeping the cross-repo view fresh is still a manual step.

**The interactive HTML viewer doesn't render inside a sandboxed AI-tool viewer.** `graph.html`
(pyvis-based) loads `vis-network.js` from `unpkg.com` at runtime — fine in a normal browser, but it
means the visualization can't be embedded in tooling with a strict content-security policy. Had to
open it directly in a browser instead of rendering it inline.

## Cost

| Run | Docs processed | Cost |
|---|---|---|
| `architecture` alone (single-repo pilot) | 23 | $0.29 |
| Full repo set, extraction + global merge | ~220 files across corpus | $2.08 |
| Cross-repo re-clustering (community naming) | — (LLM naming only, no re-extraction) | ~$0 (not separately itemized) |

Cheap enough that the real cost of this evaluation was time spent reading the source and
verifying claims, not API spend.

## What this changes going forward

An MCP server (`graphify`, registered globally, stdio transport) now gives an AI assistant working
in any of these repos direct query access to the merged graph — `query_graph`, `get_node`,
`get_neighbors`, `god_nodes`, `graph_stats`, `shortest_path` — instead of re-deriving cross-repo
structure by grep each session. Verified live: a `query_graph` call for "what connects to SYS-002"
returned the correct 27-node subgraph, including the exact `EXTRACTED` reference chain found in the
single-repo pilot.

## Credit & source

- Tool: [safishamsi/graphify](https://github.com/safishamsi/graphify) (MIT license) —
  all credit for the extraction pipeline, Leiden-based clustering approach, and MCP server design
  belongs to the original author.
- This evaluation used graphify v0.3.x against this project's own repos; findings above reflect
  behavior observed on 2026-07-02/03 and may not hold against later versions.
