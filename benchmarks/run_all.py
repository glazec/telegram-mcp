"""
Benchmark runner for the Telegram MCP search/execute dispatcher.

Runs every query through dispatcher._search_registry and measures top-1/3/5
hit rate against the iterable and frozen case sets. Appends results to
history.jsonl with git provenance so iterations can be compared honestly.

Usage:
    uv run python benchmarks/run_all.py
    uv run python benchmarks/run_all.py --note "added X"
    uv run python benchmarks/run_all.py --history
    uv run python benchmarks/run_all.py --no-record

Policy:
    - frozen_cases.py is the ONLY set that measures generalization. Never tune
      against it. See benchmarks/POLICY.md.
    - iterable_cases.py may be tuned, but track regressions across versions.
"""
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from benchmarks.iterable_cases import BENCHMARK_CASES, REAL_WORLD_CASES
from benchmarks.frozen_cases import HELDOUT_CASES

HISTORY_FILE = os.path.join(os.path.dirname(__file__), "history.jsonl")


def git_info(file_path: str = None) -> dict:
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    try:
        head = subprocess.check_output(
            ["git", "-C", repo_root, "rev-parse", "HEAD"], stderr=subprocess.DEVNULL
        ).decode().strip()
        branch = subprocess.check_output(
            ["git", "-C", repo_root, "branch", "--show-current"], stderr=subprocess.DEVNULL
        ).decode().strip()
        dirty = bool(subprocess.check_output(
            ["git", "-C", repo_root, "status", "--porcelain", "-uno"], stderr=subprocess.DEVNULL
        ).decode().strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        head, branch, dirty = "unknown", "unknown", False

    info = {"head": head[:12], "branch": branch, "dirty": dirty}
    if file_path:
        try:
            info["last_modified"] = subprocess.check_output(
                ["git", "-C", repo_root, "log", "-1", "--pretty=format:%h", "--", file_path],
                stderr=subprocess.DEVNULL,
            ).decode().strip() or "unknown"
        except (subprocess.CalledProcessError, FileNotFoundError):
            info["last_modified"] = "unknown"
    return info


def run_search_benchmark(cases: list, label: str) -> dict:
    os.environ.setdefault("DISABLE_AUTH", "true")
    os.environ.setdefault("TELEGRAM_API_ID", "1")
    os.environ.setdefault("TELEGRAM_API_HASH", "x")
    from main import _dsp_search as _search_registry

    top1, top3, top5 = 0, 0, 0
    failures = []
    for case in cases:
        results = _search_registry(case["query"], limit=5)
        names = [r["tool_name"] for r in results]
        expected = case["expected_tool"]
        alts = set(case.get("accept_alternatives", [])) | {expected}

        if names[:1] and names[0] in alts:
            top1 += 1
        else:
            failures.append({
                "query": case["query"][:80],
                "expected": expected,
                "got": names[0] if names else "NO_MATCH",
                "category": case.get("category", "?"),
            })
        if any(n in alts for n in names[:3]):
            top3 += 1
        if any(n in alts for n in names[:5]):
            top5 += 1

    n = len(cases)
    return {
        "label": label, "n": n, "top1": top1, "top3": top3, "top5": top5,
        "top1_pct": round(top1 / n * 100, 1),
        "top3_pct": round(top3 / n * 100, 1),
        "top5_pct": round(top5 / n * 100, 1),
        "failures": failures,
    }


def print_result(r: dict):
    print(f"\n  {r['label']}: {r['n']} cases")
    print(f"    Top-1: {r['top1']}/{r['n']} ({r['top1_pct']}%)")
    print(f"    Top-3: {r['top3']}/{r['n']} ({r['top3_pct']}%)")
    print(f"    Top-5: {r['top5']}/{r['n']} ({r['top5_pct']}%)")
    if r["failures"]:
        print(f"    Failures ({len(r['failures'])}):")
        for f in r["failures"]:
            print(f"      [{f['category']}] {f['query']!r}")
            print(f"        expected={f['expected']} got={f['got']}")


def show_history(n: int = 10):
    if not os.path.exists(HISTORY_FILE):
        print("No history yet.")
        return
    with open(HISTORY_FILE) as fh:
        entries = [json.loads(line) for line in fh if line.strip()]
    print(f"{'when':21s}  {'code':10s}  iter-top1  frozen-top1  frozen-top5  note")
    for e in entries[-n:]:
        ts = e["timestamp"][:19]
        code = e["git"]["code"]["head"]
        dirty = "*" if e["git"]["code"].get("dirty") else " "
        it = f"{e['results']['iterable_combined']['top1_pct']}%"
        ft1 = f"{e['results']['frozen']['top1_pct']}%"
        ft5 = f"{e['results']['frozen']['top5_pct']}%"
        print(f"  {ts}  {code}{dirty}  {it:9s}  {ft1:11s}  {ft5:11s}  {e.get('note','')[:30]}")


def main():
    parser = argparse.ArgumentParser(description="Run Telegram MCP search benchmarks")
    parser.add_argument("--note", default="")
    parser.add_argument("--no-record", action="store_true")
    parser.add_argument("--history", action="store_true")
    args = parser.parse_args()

    if args.history:
        show_history()
        return

    print("=" * 70)
    print("  Telegram MCP Benchmark — search/execute dispatcher")
    print("=" * 70)

    code_git = git_info()
    print(f"\n  Code: {code_git['head']} ({code_git['branch']}){' [DIRTY]' if code_git['dirty'] else ''}")

    syn = run_search_benchmark(BENCHMARK_CASES, f"Synthetic ({len(BENCHMARK_CASES)} cases)")
    real = run_search_benchmark(REAL_WORLD_CASES, f"Real-world ({len(REAL_WORLD_CASES)} cases)")
    combined = run_search_benchmark(BENCHMARK_CASES + REAL_WORLD_CASES,
                                    f"Iterable combined ({len(BENCHMARK_CASES) + len(REAL_WORLD_CASES)} cases)")
    frozen = run_search_benchmark(HELDOUT_CASES, f"FROZEN held-out ({len(HELDOUT_CASES)} cases)")

    print_result(syn)
    print_result(real)
    print_result(combined)
    print_result(frozen)

    print("\n" + "=" * 70)
    print(f"  SUMMARY: iterable {combined['top1_pct']}% top-1  |  "
          f"frozen {frozen['top1_pct']}% top-1 / {frozen['top5_pct']}% top-5")
    print("=" * 70)

    record = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "note": args.note,
        "git": {
            "code": code_git,
            "iterable_cases": git_info("benchmarks/iterable_cases.py"),
            "frozen_cases": git_info("benchmarks/frozen_cases.py"),
        },
        "results": {
            "synthetic": syn, "real_world": real,
            "iterable_combined": combined, "frozen": frozen,
        },
    }

    if not args.no_record:
        with open(HISTORY_FILE, "a") as fh:
            fh.write(json.dumps(record) + "\n")
        print(f"\n  Recorded to {HISTORY_FILE}")
    else:
        print("\n  Not recorded (--no-record)")


if __name__ == "__main__":
    main()
