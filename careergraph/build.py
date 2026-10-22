"""Raw threads -> knowledge graph, saved as SQLite (graph.db), JSON (knowledge_state.json) and summary.json."""

import json
import sqlite3
from bisect import bisect_left, bisect_right
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from . import config as C
from .classify import classify_comment, clean
from .credibility import score_authors
from .extract import FIELDS, experience_situation, extract_situation, thread_role

SCHEMA = {
    "node_types": {
        "Question": "Opening post of a thread. role (decision: someone weighing the choice | experience: service-company thread "
                    "used for outcome stories only), title, snippet, created, era, url, comments_used, score",
        "Situation": "Career situation parsed by the hand-written rules. current_company, current_tier, target_company, target_tier, yoe, "
                     "current_ctc, offer_ctc (LPA), notice_days, city, has_offer, stage, fields, source (question | outcome | self_report | experience_thread)",
        "Option": "One of 7 options (see config.OPTIONS). kind: decision (5, the verdict picks one) or tactic (2, shown as tips)",
        "Advice": "Comment telling someone what to do. author, author_cred, snippet, created, era, score, pct (upvote percentile in its thread), url",
        "Outcome": "Comment where the writer says what they chose and how it went. chose, polarity (good | bad | mixed | unknown) + Advice fields",
        "Factor": "Decision factor people bring up (see config.FACTORS)",
        "Author": "Reddit user. credibility and its parts: lived, outcomes, upvotes, network",
    },
    "edge_types": {
        "HAS_SITUATION": "Question -> Situation",
        "ASKED": "Author -> Question",
        "GAVE": "Author -> Advice",
        "REPORTED": "Author -> Outcome",
        "ANSWERS": "Advice -> Question",
        "RECOMMENDS": "Advice -> Option",
        "OPPOSES": "Advice -> Option",
        "CITES": "Advice -> Factor",
        "SUPPORTS": "Advice -> Advice (a reply that backs its parent)",
        "DISAGREES": "Advice -> Advice (a reply that pushes back on its parent)",
        "CHOSE": "Outcome -> Option (polarity on the edge)",
        "FROM": "Outcome -> Situation (inherited=true when the outcome stated no situation and the thread's was used)",
        "MENTIONS": "Outcome -> Factor",
        "IN_THREAD": "Outcome -> Question",
        "WAS_IN": "Author -> Situation (what the author said about their own job in these threads)",
    },
}


def read_jsonl(path):
    items = {}
    path = Path(path)
    if path.exists():
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    item = json.loads(line)
                    items[item["id"]] = item
    return items


def load_threads(raw_dir=C.RAW_DIR):
    raw = Path(raw_dir)
    sel = raw / "selected.json"
    if not sel.exists():
        return []
    posts = read_jsonl(raw / "posts.jsonl")
    threads = []
    for pid in json.loads(sel.read_text(encoding="utf-8"))["ids"]:
        path = raw / "comments" / f"{pid}.json"
        if pid in posts and path.exists():
            threads.append((posts[pid], json.loads(path.read_text(encoding="utf-8"))))
    return threads


def usable_comment(c, op_author):
    """Bots, removed text and the asker's own replies are left out."""
    author = c.get("author") or ""
    body = (c.get("body") or "").strip()
    return author not in C.BOT_AUTHORS and author != op_author and body not in ("", "[removed]", "[deleted]")


def _real(author):
    return bool(author) and author != "[deleted]" and author not in C.BOT_AUTHORS


def _percentiles(scores):
    n = len(scores)
    if n <= 1:
        return [0.5] * n
    ordered = sorted(scores)
    return [(bisect_left(ordered, s) + 0.5 * (bisect_right(ordered, s) - bisect_left(ordered, s) - 1)) / (n - 1) for s in scores]


def stance_relation(child, parent):
    for opt, st in child.items():
        if parent.get(opt) == -st:
            return "DISAGREES"
    for opt, st in child.items():
        for popt, pst in parent.items():
            if st > 0 and pst > 0 and frozenset((opt, popt)) in C.CONFLICTING_OPTIONS:
                return "DISAGREES"
    for opt, st in child.items():
        if parent.get(opt) == st:
            return "SUPPORTS"
    return None


class Graph:
    def __init__(self):
        self.nodes, self.edges = {}, []

    def node(self, nid, ntype, **props):
        node = self.nodes.setdefault(nid, {"id": nid, "type": ntype})
        node.update({k: v for k, v in props.items() if v is not None or k not in node})
        return nid

    def edge(self, src, dst, etype, **props):
        self.edges.append({"src": src, "dst": dst, "type": etype, **props})


def build(threads, out_dir=C.STATE_DIR, min_comments=C.MIN_COMMENTS, max_threads=C.MAX_THREADS, source="Arctic Shift archive"):
    pools = {"decision": [], "experience": []}
    seen = set()
    for post, comments in threads:
        role = thread_role(post.get("title"), post.get("selftext"))
        real = []
        for c in comments:
            if not usable_comment(c, post.get("author")):
                continue
            key = (c.get("author"), " ".join((c.get("body") or "").split()))
            if _real(c.get("author")) and key in seen:
                continue                        # the same person posting the same comment twice
            seen.add(key)
            real.append(c)
        if role and len(real) >= min_comments:
            pools[role].append((post, real, role))
    for pool in pools.values():
        pool.sort(key=lambda t: len(t[1]), reverse=True)
    usable = pools["decision"][:max_threads] + pools["experience"][:C.EXPERIENCE_THREADS]

    g = Graph()
    for key, label in C.OPTIONS.items():
        g.node(f"opt:{key}", "Option", key=key, label=label, kind="tactic" if key in C.TACTICS else "decision")
    for key, label in C.FACTORS.items():
        g.node(f"f:{key}", "Factor", key=key, label=label)
    stats = defaultdict(lambda: {"pcts": [], "outcomes": 0, "self": None, "experience": False})
    helps = defaultdict(lambda: defaultdict(float))
    kinds = Counter()

    for post, comments, role in usable:
        pid, op = post["id"], post.get("author")
        qid, sid = f"q:{pid}", f"s:q:{pid}"
        body = post.get("selftext") or ""
        body = "" if body.strip() in ("[removed]", "[deleted]") else body
        created = C.iso_date(post["created_utc"])
        if role == "experience":
            sit = experience_situation(post.get("title", ""))
        else:
            sit = extract_situation(clean(f"{post.get('title', '')}\n{body}"))
        g.node(qid, "Question", title=post.get("title", ""), snippet=C.snippet(clean(body)), created=created,
               era=C.era_of(created)[0], url=C.post_url(pid), comments_used=len(comments), score=post.get("score") or 0, role=role)
        g.node(sid, "Situation", source="question" if role == "decision" else "experience_thread", **sit)
        g.edge(qid, sid, "HAS_SITUATION")
        if _real(op):
            g.node(f"u:{op}", "Author", name=op)
            g.edge(f"u:{op}", qid, "ASKED")

        by_id = {c["id"]: c for c in comments}
        results = {}
        for c, pct in zip(comments, _percentiles([c.get("score") or 0 for c in comments])):
            r = classify_comment(c.get("body") or "", sit)
            results[c["id"]] = r
            kinds[r["kind"]] += 1
            if r["kind"] == "noise" or (role == "experience" and not r["is_outcome"]):
                continue                        # experience threads only contribute outcome stories
            cid, author = c["id"], c.get("author")
            uid = f"u:{author}" if _real(author) else None
            when = C.iso_date(c["created_utc"])
            common = dict(author=author if uid else None, snippet=C.snippet(r["text"]), created=when, era=C.era_of(when)[0],
                          score=c.get("score") or 0, pct=round(pct, 3), url=C.comment_url(pid, cid))
            if uid:
                a = stats[uid]
                a["pcts"].append(pct)
                if r["self_situation"] and len(r["self_situation"]["fields"]) > len((a["self"] or {}).get("fields", [])):
                    a["self"] = r["self_situation"]
                a["experience"] = a["experience"] or r["experience"]
                parent = c.get("parent_id") or ""
                asker = op if parent.startswith("t3_") else by_id.get(parent[3:], {}).get("author")
                if _real(asker) and asker != author:
                    helps[f"u:{asker}"][uid] += 1.0
            chose = None
            if r["is_outcome"]:
                out = r["outcome"]
                chose = out["chose"]
                oid = g.node(f"out:{cid}", "Outcome", chose=chose, polarity=out["polarity"], **common)
                g.edge(oid, f"opt:{chose}", "CHOSE", polarity=out["polarity"])
                g.edge(oid, qid, "IN_THREAD")
                if out["situation"]:
                    g.edge(oid, g.node(f"s:o:{cid}", "Situation", source="outcome", **out["situation"]), "FROM", inherited=False)
                else:
                    g.edge(oid, sid, "FROM", inherited=True)
                for f in r["factors"]:
                    g.edge(oid, f"f:{f}", "MENTIONS")
                if uid:
                    stats[uid]["outcomes"] += 1
                    g.edge(uid, oid, "REPORTED")
            if r["is_advice"] and role == "decision":
                aid = g.node(f"adv:{cid}", "Advice", **common)
                g.edge(aid, qid, "ANSWERS")
                for opt, st in r["stances"].items():
                    if st > 0 and opt == chose:
                        continue   # the same comment already counts for this option as an outcome
                    g.edge(aid, f"opt:{opt}", "RECOMMENDS" if st > 0 else "OPPOSES")
                for f in r["factors"]:
                    g.edge(aid, f"f:{f}", "CITES")
                if uid:
                    g.edge(uid, aid, "GAVE")

        for c in comments:                      # replies between two advice comments
            r, parent = results[c["id"]], c.get("parent_id") or ""
            pr = results.get(parent[3:]) if parent.startswith("t1_") else None
            if role == "decision" and r["is_advice"] and pr and pr["is_advice"]:
                rel = r["reply_hint"] or stance_relation(r["stances"], pr["stances"])
                if rel:
                    g.edge(f"adv:{c['id']}", f"adv:{parent[3:]}", rel)

    cred = score_authors(stats, helps)
    for uid, parts in cred.items():
        g.node(uid, "Author", name=uid[2:], **parts)
        if stats[uid]["self"]:
            g.edge(uid, g.node(f"s:a:{uid[2:]}", "Situation", source="self_report", **stats[uid]["self"]), "WAS_IN")
    for node in g.nodes.values():
        if node["type"] in ("Advice", "Outcome"):
            uid = f"u:{node['author']}" if node.get("author") else None
            node["author_cred"] = cred[uid]["credibility"] if uid in cred else round(C.CRED_WEIGHTS["upvotes"] * node["pct"], 4)

    dates = sorted(n["created"] for n in g.nodes.values() if n["type"] == "Question")
    meta = {
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": source,
        "subreddit": C.SUBREDDIT,
        "threads": len(usable),
        "thread_roles": dict(Counter(role for _, _, role in usable)),
        "date_range": [dates[0], dates[-1]] if dates else None,
        "comment_kinds": dict(kinds),
        "node_counts": dict(Counter(n["type"] for n in g.nodes.values())),
        "edge_counts": dict(Counter(e["type"] for e in g.edges)),
        "settings": {"type_weight": C.TYPE_WEIGHT, "cred_weights": C.CRED_WEIGHTS, "eras": C.ERAS,
                     "match_weights": C.MATCH_WEIGHTS, "min_comments": min_comments, "max_threads": max_threads},
    }
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    _save_sqlite(g, out / "graph.db", meta)
    _save_json(g, out / "knowledge_state.json", meta)
    (out / "summary.json").write_text(json.dumps(_summary(g, meta), indent=2, ensure_ascii=False), encoding="utf-8")
    return meta


def _strip(d, keys):
    return {k: v for k, v in d.items() if k not in keys}


def _save_sqlite(g, path, meta):
    con = sqlite3.connect(path)
    con.execute("PRAGMA journal_mode=MEMORY")
    con.executescript("""
        DROP TABLE IF EXISTS nodes; DROP TABLE IF EXISTS edges; DROP TABLE IF EXISTS meta;
        CREATE TABLE nodes (id TEXT PRIMARY KEY, type TEXT NOT NULL, props TEXT NOT NULL);
        CREATE TABLE edges (src TEXT NOT NULL, dst TEXT NOT NULL, type TEXT NOT NULL, props TEXT);
        CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE INDEX idx_nodes_type ON nodes(type);
        CREATE INDEX idx_edges_src ON edges(src, type);
        CREATE INDEX idx_edges_dst ON edges(dst, type);
    """)
    con.executemany("INSERT INTO nodes VALUES (?, ?, ?)",
                    [(n["id"], n["type"], json.dumps(_strip(n, ("id", "type")), ensure_ascii=False)) for n in g.nodes.values()])
    con.executemany("INSERT INTO edges VALUES (?, ?, ?, ?)",
                    [(e["src"], e["dst"], e["type"], json.dumps(_strip(e, ("src", "dst", "type")))) for e in g.edges])
    con.executemany("INSERT INTO meta VALUES (?, ?)", [(k, json.dumps(v, ensure_ascii=False)) for k, v in meta.items()])
    con.commit()
    con.close()


def _save_json(g, path, meta):
    """One node or edge per line, so the file is readable in any editor and still valid JSON."""
    by_type = defaultdict(list)
    for n in g.nodes.values():
        by_type[n["type"]].append(n)
    with open(path, "w", encoding="utf-8") as f:
        f.write('{\n"meta": ' + json.dumps(meta, indent=1, ensure_ascii=False) + ",\n")
        f.write('"schema": ' + json.dumps(SCHEMA, indent=1) + ",\n")
        f.write('"nodes": {\n')
        types = list(by_type)
        for i, t in enumerate(types):
            f.write(json.dumps(t) + ": [\n" + ",\n".join(json.dumps(n, ensure_ascii=False) for n in by_type[t]))
            f.write("\n]" + ("," if i < len(types) - 1 else "") + "\n")
        f.write('},\n"edges": [\n' + ",\n".join(json.dumps(e, ensure_ascii=False) for e in g.edges) + "\n]\n}\n")


def _summary(g, meta):
    outcomes, stances, factors = defaultdict(Counter), defaultdict(Counter), defaultdict(Counter)
    for e in g.edges:
        t = e["type"]
        if t == "CHOSE":
            outcomes[e["dst"][4:]][e["polarity"]] += 1
        elif t in ("RECOMMENDS", "OPPOSES"):
            stances[e["dst"][4:]][t.lower()] += 1
        elif t == "CITES":
            factors[e["dst"][2:]]["advice"] += 1
        elif t == "MENTIONS":
            factors[e["dst"][2:]][g.nodes[e["src"]]["polarity"] + "_outcomes"] += 1
    qs = [n for n in g.nodes.values() if n["type"] == "Situation" and n.get("source") == "question"]
    authors = sorted((n for n in g.nodes.values() if n["type"] == "Author" and "credibility" in n),
                     key=lambda n: n["credibility"], reverse=True)[:15]
    return {
        "meta": meta,
        "threads_by_year": dict(sorted(Counter(n["created"][:4] for n in g.nodes.values() if n["type"] == "Question").items())),
        "question_situation_field_coverage": {f: round(sum(1 for s in qs if s.get(f) is not None) / len(qs), 3) for f in FIELDS} if qs else {},
        "advice_stances_by_option": {k: dict(v) for k, v in stances.items()},
        "outcomes_by_option": {k: dict(v) for k, v in outcomes.items()},
        "factor_mentions": {k: dict(v) for k, v in factors.items()},
        "top_authors_by_credibility": [{k: n.get(k) for k in ("name", "credibility", "lived", "outcomes", "upvotes", "network", "comments", "outcome_reports")} for n in authors],
    }
