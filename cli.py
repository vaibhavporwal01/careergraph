"""Command line entry point. Run `python cli.py -h` for the commands."""

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path

from careergraph import config as C


def cmd_fetch(a):
    from careergraph.fetch import run
    run(stage=a.stage, since=a.since, until=a.until or date.today().isoformat(), max_threads=a.max_threads)


def cmd_build(a):
    from careergraph.build import build, load_threads
    threads = load_threads(a.raw)
    if not threads:
        sys.exit("No threads in data/raw yet. Run `python cli.py fetch` first.")
    meta = build(threads, a.out, min_comments=a.min_comments, max_threads=a.max_threads)
    print(json.dumps({k: meta[k] for k in ("threads", "thread_roles", "date_range", "comment_kinds", "node_counts", "edge_counts")}, indent=2))
    print(f"Knowledge state written to {a.out}")


def cmd_ask(a):
    from careergraph.reason import KnowledgeGraph, answer
    from careergraph.render import render
    if a.file:
        text = Path(a.file).read_text(encoding="utf-8")
    elif a.text:
        text = " ".join(a.text)
    else:
        text = input("Describe your situation: ")
    try:
        kg = KnowledgeGraph(a.state)
    except FileNotFoundError as e:
        sys.exit(str(e))
    verdict = answer(kg, text)
    print(json.dumps(verdict, indent=2, ensure_ascii=False) if a.json else render(verdict))
    if not a.no_save:
        C.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        path = C.OUTPUT_DIR / f"verdict_{datetime.now():%Y%m%d_%H%M%S}.json"
        path.write_text(json.dumps(verdict, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nSaved: {path}")


def cmd_stats(a):
    path = Path(a.state) / "summary.json"
    if not path.exists():
        sys.exit("No summary yet. Run `python cli.py build` first.")
    print(path.read_text(encoding="utf-8"))


def cmd_label_sample(a):
    from careergraph.evaluate import make_sheets
    try:
        n, k = make_sheets(n=a.n, n_outcomes=a.outcomes, seed=a.seed, force=a.force)
    except FileExistsError as e:
        sys.exit(str(e))
    print(f"Wrote {n} random comments to {C.EVAL_DIR / 'labels.csv'} and {k} outcome stories to "
          f"{C.EVAL_DIR / 'outcome_audit.csv'}. Fill in the label columns, then run `python cli.py eval`.")


def cmd_eval(a):
    from careergraph.evaluate import evaluate
    print(json.dumps(evaluate(), indent=2))


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    p = argparse.ArgumentParser(prog="python cli.py", description="Service vs product career decisions from r/developersIndia, as a knowledge graph.")
    sub = p.add_subparsers(dest="cmd", required=True)

    f = sub.add_parser("fetch", help="download the data subset from Arctic Shift (resumable)")
    f.add_argument("--since", default=C.DATE_FROM, help=f"first day to list (default {C.DATE_FROM})")
    f.add_argument("--until", default=None, help="day to stop before (default today)")
    f.add_argument("--stage", choices=["all", "listing", "bodies", "comments"], default="all")
    f.add_argument("--max-threads", type=int, default=C.FETCH_COMMENTS_FOR, help="threads whose comments get downloaded")
    f.set_defaults(func=cmd_fetch)

    b = sub.add_parser("build", help="build the knowledge graph from data/raw")
    b.add_argument("--raw", type=Path, default=C.RAW_DIR)
    b.add_argument("--out", type=Path, default=C.STATE_DIR)
    b.add_argument("--min-comments", type=int, default=C.MIN_COMMENTS)
    b.add_argument("--max-threads", type=int, default=C.MAX_THREADS)
    b.set_defaults(func=cmd_build)

    q = sub.add_parser("ask", help="describe a new situation and get a structured verdict")
    q.add_argument("text", nargs="*", help="your situation in plain words")
    q.add_argument("--file", help="read the situation from a text file instead")
    q.add_argument("--json", action="store_true", help="print the raw JSON verdict")
    q.add_argument("--no-save", action="store_true", help="do not save the verdict to outputs/")
    q.add_argument("--state", type=Path, default=C.STATE_DIR)
    q.set_defaults(func=cmd_ask)

    s = sub.add_parser("stats", help="print knowledge_state/summary.json")
    s.add_argument("--state", type=Path, default=C.STATE_DIR)
    s.set_defaults(func=cmd_stats)

    l = sub.add_parser("label-sample", help="write comments to label into eval/ (random sample + outcome story audit)")
    l.add_argument("--n", type=int, default=150, help="random comments to label")
    l.add_argument("--outcomes", type=int, default=50, help="outcome stories to audit")
    l.add_argument("--seed", type=int, default=7)
    l.add_argument("--force", action="store_true", help="overwrite sheets that already have labels")
    l.set_defaults(func=cmd_label_sample)

    e = sub.add_parser("eval", help="compare the current comment rules with the labels in eval/")
    e.set_defaults(func=cmd_eval)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
