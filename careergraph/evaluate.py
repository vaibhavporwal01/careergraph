"""Checks the comment rules against labels.
1. `python cli.py label-sample` writes two sheets with the label columns empty:
   - eval/labels.csv: random comments from the downloaded threads, to label advice / outcome / both / noise
   - eval/outcome_audit.csv: comments the rules read as outcome stories, to check if each really is one,
     what the writer chose and how it went
2. Fill in the label columns (definitions in approach.md).
3. `python cli.py eval` runs the current rules on the same comments and writes eval/results.json.
The comment text and its thread context are saved in eval/context.json, so eval works without the raw
data and always measures the rules as they are now."""

import csv
import json
import random
from collections import Counter

from . import config as C
from .build import load_threads, usable_comment
from .classify import classify_comment, clean
from .extract import experience_situation, extract_situation, thread_role

LABELS = {"advice", "outcome", "both", "noise"}
YES, NO = {"yes", "y"}, {"no", "n"}
SHEET, AUDIT, CONTEXT = "labels.csv", "outcome_audit.csv", "context.json"


def thread_context(post):
    """The same thread Situation the build uses, so the rules see each comment the way they did in the graph."""
    if thread_role(post.get("title"), post.get("selftext")) == "experience":
        return experience_situation(post.get("title", ""))
    return extract_situation(clean(f"{post.get('title', '')}\n{post.get('selftext') or ''}"))


def _rows(path):
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.reader(f))[1:]


def _has_labels(eval_dir):
    return (any(len(r) >= 4 and r[3].strip() for r in _rows(eval_dir / SHEET))
            or any(len(r) >= 6 and r[5].strip() for r in _rows(eval_dir / AUDIT)))


def make_sheets(n=150, n_outcomes=50, seed=7, force=False, raw_dir=C.RAW_DIR, state_dir=C.STATE_DIR, eval_dir=C.EVAL_DIR):
    if not force and _has_labels(eval_dir):
        raise FileExistsError(f"{eval_dir} already has labels. Use --force to overwrite them.")
    from .reason import KnowledgeGraph
    pool, by_id = [], {}
    for post, comments in load_threads(raw_dir):
        ctx = thread_context(post)
        for c in comments:
            if usable_comment(c, post.get("author")):
                pool.append((post, c, ctx))
                by_id[c["id"]] = (post, c, ctx)
    rng = random.Random(seed)
    sample = rng.sample(pool, min(n, len(pool)))
    kg = KnowledgeGraph(state_dir)
    story_ids = sorted(oid[4:] for oid in kg.by_type["Outcome"] if oid[4:] in by_id)
    audit = [by_id[i] for i in rng.sample(story_ids, min(n_outcomes, len(story_ids)))]

    eval_dir.mkdir(parents=True, exist_ok=True)
    context = {}
    with open(eval_dir / SHEET, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["comment_id", "thread_title", "comment", "label (advice/outcome/both/noise)"])
        for post, c, ctx in sample:
            context[c["id"]] = {"text": c.get("body") or "", "ctx": ctx}
            w.writerow([c["id"], post.get("title") or "", c.get("body") or "", ""])
    with open(eval_dir / AUDIT, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["comment_id", "thread_title", "comment", "rule_chose", "rule_result", "really a story? (yes/no)",
                    "what they chose (option key, see config.OPTIONS)", "how it went (good/bad/mixed/unknown)"])
        for post, c, ctx in audit:
            out = classify_comment(c.get("body") or "", ctx)["outcome"] or {}
            context[c["id"]] = {"text": c.get("body") or "", "ctx": ctx}
            w.writerow([c["id"], post.get("title") or "", c.get("body") or "", out.get("chose", ""), out.get("polarity", ""), "", "", ""])
    (eval_dir / CONTEXT).write_text(json.dumps(context, ensure_ascii=False, indent=1), encoding="utf-8")
    return len(sample), len(audit)


def _pr(tp, fp, fn):
    return {"precision": round(tp / (tp + fp), 3) if tp + fp else None,
            "recall": round(tp / (tp + fn), 3) if tp + fn else None, "tp": tp, "fp": fp, "fn": fn}


def evaluate(eval_dir=C.EVAL_DIR):
    context = json.loads((eval_dir / CONTEXT).read_text(encoding="utf-8"))

    def run(cid):
        return classify_comment(context[cid]["text"], context[cid]["ctx"])

    result = {}
    gold = {r[0]: r[3].strip().lower() for r in _rows(eval_dir / SHEET) if len(r) >= 4 and r[3].strip().lower() in LABELS}
    if gold:
        preds = {cid: run(cid) for cid in gold}
        result["random_comments"] = {"labeled": len(gold), "labels": dict(Counter(gold.values()))}
        for name, key in (("advice", "is_advice"), ("outcome", "is_outcome")):
            tp = fp = fn = 0
            for cid, label in gold.items():
                truth, pred = label in (name, "both"), preds[cid][key]
                tp += truth and pred
                fp += pred and not truth
                fn += truth and not pred
            result["random_comments"][name] = _pr(tp, fp, fn)
    audit = [r for r in _rows(eval_dir / AUDIT) if len(r) >= 8 and r[5].strip().lower() in YES | NO]
    if audit:
        still = real = chose_ok = result_ok = 0
        for r in audit:
            res = run(r[0])
            if not res["is_outcome"]:
                continue                          # the current rules no longer read it as a story
            still += 1
            if r[5].strip().lower() in YES:
                real += 1
                chose_ok += res["outcome"]["chose"] == r[6].strip()
                result_ok += res["outcome"]["polarity"] == r[7].strip().lower()
        result["outcome_stories"] = {
            "audited": len(audit), "still_read_as_story": still, "really_a_story": real,
            "choice_right": chose_ok, "result_right": result_ok,
            "story_precision": round(real / still, 3) if still else None,
            "choice_accuracy": round(chose_ok / real, 3) if real else None,
            "result_accuracy": round(result_ok / real, 3) if real else None,
        }
    (eval_dir / "results.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    return result
