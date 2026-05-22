# Benchmark Policy

Why this exists: when you tune the search algorithm against the same test cases
that measure its quality, you overfit silently. Production accuracy drops
without warning. This policy keeps measurement honest.

## Two-tier structure

| Tier | File | Cases | Role | Tuning allowed? |
|---|---|---|---|---|
| **Iterable** | `iterable_cases.py` | grow as you build | Development feedback, regression detection | **Yes** — tune freely |
| **Frozen** | `frozen_cases.py` | small, append-only | True generalization estimate | **No — see rules below** |

## Frozen-set rules

The frozen set is the **only honest measurement** of how well the server
generalizes to unseen queries. Its integrity depends on these rules.

### Rule 1 — never tune the algorithm to pass frozen cases

If you change `_search_registry`, `TOOL_REGISTRY` keywords, signal
vocabularies, or any scoring logic in `main.py`, you MUST NOT look at frozen-set
failures beforehand and reverse-engineer fixes for them.

Acceptable workflow:
```
1. Change main.py based on iterable-set failures or new requirements.
2. Run benchmarks/run_all.py.
3. Record whatever the frozen score is — good or bad.
4. Do NOT go back and tweak the algorithm to lift the frozen score.
```

If you find yourself thinking *"the frozen set fails on X, let me add a rule
for X"* — stop. That's overfitting. Add an X-shaped case to the iterable set
instead, and accept that the frozen set will catch the next variant of X.

### Rule 2 — only add to the frozen set from older sources

New frozen cases must be extracted from documents written BEFORE the current
algorithm version was tuned. Specifically:

- User transcripts / logs predating the last `_search_registry` commit
- Tickets, issues, design docs from before the current branch
- Real customer queries captured via telemetry (e.g. PostHog) BEFORE you saw them

Do NOT add cases that you wrote, paraphrased, or saw during algorithm tuning.
If a case sounds too convenient or fits a fix you just made, exclude it.

### Rule 3 — frozen-set growth requires its own commit

When you add cases to `frozen_cases.py`, commit that change SEPARATELY from
any `main.py` change. The git history then shows "the algorithm at hash X was
scored against the test set at hash Y."

Two commit messages:
```
benchmarks: add 10 new frozen cases from Q2 ticket samples   # touches only frozen_cases.py
search: tighten dominance-vs-details disambiguation          # touches only main.py
```

## Iterable-set rules

### Rule 4 — tuning is allowed, but track regressions

The iterable set is for development feedback. You can add, remove, or
paraphrase cases freely. But every `benchmarks/run_all.py` invocation appends
to `history.jsonl`, so regressions across versions are visible in the log.

If a refactor drops iterable score by >2pp, investigate before merging.

### Rule 5 — categorize new iterable cases

When adding cases, set:
- `category` — match one of TOOL_CATEGORIES from main.py
- `difficulty` — easy / medium / hard
- `source` — where it came from (e.g. `adversarial/paraphrase`, `customer-ticket-1234`, `coverage/new-tool-X`)

The source field lets you see if the iterable set drifts toward a specific
source (another overfitting risk).

## Run policy

```bash
# Standard run — appends to history.jsonl
uv run python benchmarks/run_all.py

# Annotate the run
uv run python benchmarks/run_all.py --note "added foo_tool"

# Dry run (don't pollute history during local debugging)
uv run python benchmarks/run_all.py --no-record

# Show recent history
uv run python benchmarks/run_all.py --history
```

## What history.jsonl tracks

Each line is one benchmark run:

```json
{
  "timestamp": "2026-05-20T03:30:00Z",
  "note": "...",
  "git": {
    "code":           {"head": "abc123def456", "branch": "...", "dirty": false},
    "iterable_cases": {"last_modified": "fedcba98"},
    "frozen_cases":   {"last_modified": "1234abcd"}
  },
  "results": {
    "iterable_combined": {"top1_pct": 100.0, "top5_pct": 100.0, ...},
    "frozen":            {"top1_pct": 68.0, "top5_pct": 96.0, ...}
  }
}
```

The three independent git hashes — code, iterable, frozen — make it explicit
which version of each was used. A score is only meaningful when tied to a
`(code, frozen)` pair.

## How to interpret divergence

- **Iterable up, frozen flat:** healthy generalization. Rules cover real
  failure modes without overfitting.
- **Iterable up, frozen down:** classic overfitting — revert.
- **Iterable flat, frozen up:** lucky — investigate why; maybe a synonym you
  added incidentally covers a frozen-set case.
- **Both down:** broke something. Don't merge.

The number to optimize is **frozen top-5**, not iterable top-1. Top-5 measures
recall in the candidate set, which is what production uses (the LLM reranks
from search results).
