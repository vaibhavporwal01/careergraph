"""Answers a new situation by reasoning over the saved graph:
parse it with the same rules -> match similar situations through their attributes ->
weigh advice and outcomes by credibility, era and similarity -> surface dissent and blind spots."""

import json
import math
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

from . import config as C
from .classify import clean
from .extract import extract_situation


class KnowledgeGraph:
    def __init__(self, state_dir=C.STATE_DIR):
        db = Path(state_dir) / "graph.db"
        if not db.exists():
            raise FileNotFoundError(f"No graph at {db}. Run `python cli.py build` first.")
        con = sqlite3.connect(db)
        self.nodes, self.out = {}, defaultdict(list)
        for nid, ntype, props in con.execute("SELECT id, type, props FROM nodes"):
            node = json.loads(props)
            node.update(id=nid, type=ntype)
            self.nodes[nid] = node
        for src, dst, etype, props in con.execute("SELECT src, dst, type, props FROM edges"):
            self.out[src].append((etype, dst, json.loads(props) if props else {}))
        self.meta = {k: json.loads(v) for k, v in con.execute("SELECT key, value FROM meta")}
        con.close()
        self.by_type = defaultdict(list)
        for nid, node in self.nodes.items():
            self.by_type[node["type"]].append(nid)
        self.q_situation, self.answers, self.factors = {}, defaultdict(list), defaultdict(set)
        for src, edges in self.out.items():
            for etype, dst, _ in edges:
                if etype == "HAS_SITUATION" and self.nodes[src].get("role", "decision") == "decision":
                    self.q_situation[src] = dst   # only decision threads are matched for advice
                elif etype == "ANSWERS":
                    self.answers[dst].append(src)
                elif etype in ("CITES", "MENTIONS"):
                    self.factors[src].add(dst[2:])

    def edges(self, nid, etype):
        return [(dst, props) for t, dst, props in self.out.get(nid, []) if t == etype]


def _tier_sim(a, b):
    if a is None or b is None:
        return None
    return 1.0 if a == b else C.TIER_SIMILARITY.get(frozenset((a, b)), 0.0)


def similarity(q, s):
    """Weighted attribute match (tier 0.5, YOE 0.3, CTC 0.2), lowered when fields are missing on either side."""
    parts = {}
    cur = _tier_sim(q.get("current_tier"), s.get("current_tier"))
    tgt = _tier_sim(q.get("target_tier"), s.get("target_tier"))
    if cur is not None and tgt is not None:
        parts["tier"] = 0.6 * cur + 0.4 * tgt
    elif cur is not None or tgt is not None:
        parts["tier"] = cur if cur is not None else tgt
    if q.get("yoe") is not None and s.get("yoe") is not None:
        parts["yoe"] = max(0.0, 1 - abs(q["yoe"] - s["yoe"]) / C.YOE_ZERO_AT)
    for key in ("current_ctc", "offer_ctc"):
        if q.get(key) and s.get(key):
            parts["ctc"] = max(0.0, 1 - abs(math.log(q[key] / s[key])) / math.log(C.CTC_ZERO_RATIO))
            break
    if "tier" not in parts and "yoe" not in parts:
        return None
    have = sum(C.MATCH_WEIGHTS[k] for k in parts)
    base = sum(C.MATCH_WEIGHTS[k] * v for k, v in parts.items()) / have
    coverage = have / sum(C.MATCH_WEIGHTS.values())
    return base * (C.MISSING_FIELD_FLOOR + (1 - C.MISSING_FIELD_FLOOR) * coverage)


def position(sit):
    """Where the asker stands, which decides the decisions that fit (config.APPLICABLE)."""
    if sit.get("stage") == "fresher" or sit.get("current_tier") == "fresher":
        return "fresher"
    if sit.get("has_offer") and sit.get("target_tier") in ("product", "startup"):
        return "offer_in_hand"
    if sit.get("stage") == "employed" or sit.get("current_tier") in ("service", "product", "startup"):
        return "employed"
    return None


def _cred_factor(cred):
    return C.CRED_FLOOR + (1 - C.CRED_FLOOR) * cred


def brief(s):
    def side(company, tier):
        return f"{company} ({tier})" if company and tier else (company or tier or "?")
    bits = [side(s.get("current_company"), s.get("current_tier"))]
    if s.get("yoe") is not None:
        bits.append(f"{s['yoe']:g} YOE")
    if s.get("current_ctc"):
        bits.append(f"{s['current_ctc']:g} LPA")
    text = ", ".join(bits)
    if s.get("target_tier") or s.get("offer_ctc"):
        text += " -> " + side(s.get("target_company"), s.get("target_tier"))
        if s.get("offer_ctc"):
            text += f" at {s['offer_ctc']:g} LPA"
    return text


def _quote(kg, nid):
    n = kg.nodes[nid]
    return {"author": n.get("author"), "year": n["created"][:4], "snippet": n["snippet"], "url": n["url"]}


def _disagreements(kg, advice_ids, option):
    target = f"opt:{option}"
    count = 0
    for aid in set(advice_ids):
        for dst, _ in kg.edges(aid, "DISAGREES"):
            if any(target in {d for d, _ in kg.edges(x, "RECOMMENDS")} for x in (aid, dst)):
                count += 1
    return count


def answer(kg, text):
    sit = extract_situation(clean(text))
    v = {"input": text.strip(), "parsed_situation": sit, "position": None, "recommendation": None, "tips": [], "evidence_base": {}, "option_scores": [],
         "dissent": None, "outcomes": [], "risk_flags": [], "credible_voices": [], "matched_threads": [], "warnings": []}
    warn = v["warnings"]
    if sit["current_tier"] is None and sit["target_tier"] is None and sit["yoe"] is None:
        warn.append("No company type or years of experience found in the input, so nothing can be matched. "
                    "Say where you work (or that you are a fresher) and how long you have worked.")
        return v
    where = position(sit)
    v["position"] = where
    fits = C.APPLICABLE.get(where, C.MAIN_OPTIONS)
    remap_adv, remap_out = C.REMAP_ADVICE.get(where, {}), C.REMAP_OUTCOMES.get(where, {})
    for field, label in (("current_tier", "current company type"), ("yoe", "years of experience"), ("current_ctc", "current CTC")):
        if sit[field] is None and not (where == "fresher" and field == "current_ctc"):
            warn.append(f"No {label} found in the input; matching on the rest with lower similarity.")

    # 1. similar situations: thread questions, and outcomes through their own situation
    threads = []
    for qid, sid in kg.q_situation.items():
        s = similarity(sit, kg.nodes[sid])
        if s is not None and s >= C.MIN_SIMILARITY:
            threads.append((s, qid))
    threads = sorted(threads, reverse=True)[: C.TOP_K_SITUATIONS]
    outcomes = []
    for oid in kg.by_type["Outcome"]:
        for sid, props in kg.edges(oid, "FROM"):
            s = similarity(sit, kg.nodes[sid])
            if s is not None and props.get("inherited"):
                s *= C.INHERITED_SITUATION_DISCOUNT
            if s is not None and s >= C.MIN_SIMILARITY:
                outcomes.append((s, oid))
    outcomes = sorted(outcomes, reverse=True)[: C.MAX_OUTCOMES]

    # 2. weigh evidence per option
    pos, neg = defaultdict(float), defaultdict(float)
    tally = {o: Counter() for o in C.OPTIONS}
    stance_n = {o: Counter() for o in C.OPTIONS}
    voices = defaultdict(lambda: {"weight": 0.0, "lean": defaultdict(float), "url": None})
    best = {}
    advice_ids, era_mass = [], defaultdict(float)

    def note(author, opt, w, sign, nid, era):
        era_mass[era] += w
        if author:
            voice = voices[author]
            voice["weight"] += w
            voice["lean"][opt] += sign * w
            voice["url"] = voice["url"] or kg.nodes[nid]["url"]
        if w > best.get((opt, sign), (0, None))[0]:
            best[(opt, sign)] = (w, nid)

    for sim, qid in threads:
        for aid in kg.answers.get(qid, []):
            a = kg.nodes[aid]
            advice_ids.append(aid)
            era, era_w = C.era_of(a["created"])
            w = C.TYPE_WEIGHT["advice"] * _cred_factor(a.get("author_cred", 0.1)) * era_w * sim
            done = set()
            for etype, sign, bucket in (("RECOMMENDS", 1, pos), ("OPPOSES", -1, neg)):
                for opt_id, _ in kg.edges(aid, etype):
                    opt = remap_adv.get(opt_id[4:], opt_id[4:])
                    if (opt, sign) in done:
                        continue
                    done.add((opt, sign))
                    bucket[opt] += w
                    stance_n[opt][etype.lower()] += 1
                    note(a.get("author"), opt, w, sign, aid, era)
    shown = []
    for sim, oid in outcomes:
        o = kg.nodes[oid]
        opt, pol = remap_out.get(o["chose"], o["chose"]), o["polarity"]
        era, era_w = C.era_of(o["created"])
        w = C.TYPE_WEIGHT["outcome"] * _cred_factor(o.get("author_cred", 0.1)) * era_w * sim
        tally[opt][pol] += 1
        if pol == "good":
            pos[opt] += w
            note(o.get("author"), opt, w, 1, oid, era)
        elif pol == "bad":
            neg[opt] += w
            note(o.get("author"), opt, w, -1, oid, era)
        elif pol == "mixed":
            pos[opt] += w / 2
            neg[opt] += w / 2
        shown.append((w, sim, oid))

    scores = [{"option": o, "label": label, "net": round(pos[o] - neg[o], 3), "support": round(pos[o], 3), "against": round(neg[o], 3),
               "advice": {"recommends": stance_n[o]["recommends"], "opposes": stance_n[o]["opposes"]},
               "outcomes": {k: tally[o][k] for k in ("good", "bad", "mixed", "unknown")}} for o, label in C.OPTIONS.items()]
    scores.sort(key=lambda r: r["net"], reverse=True)
    main = [r for r in scores if r["option"] in fits]   # the verdict picks from decisions that fit the asker
    n_sit = len(threads)
    n_out = sum(1 for _, oid in outcomes if kg.nodes[oid]["polarity"] != "unknown")
    v["option_scores"] = main
    v["evidence_base"] = {"similar_situations": n_sit, "advice_comments": len(advice_ids), "outcome_reports": n_out,
                          "graph_size": {t: len(kg.by_type[t]) for t in ("Question", "Advice", "Outcome", "Author")}}
    v["matched_threads"] = [{"title": kg.nodes[q]["title"], "similarity": round(s, 2), "situation": brief(kg.nodes[kg.q_situation[q]]),
                             "url": kg.nodes[q]["url"]} for s, q in threads[:5]]

    # 3. verdict and confidence
    top = main[0] if main and main[0]["net"] > 0 else None
    if top is None:
        warn.append("No decision has more support than pushback for situations like this one.")
    else:
        positive = sum(r["net"] for r in main if r["net"] > 0)
        share = top["net"] / positive
        # confidence counts outcome reports for the recommended option only
        top_out = sum(top["outcomes"][k] for k in ("good", "bad", "mixed"))
        if top_out == 0:
            warn.append(f"Nobody in similar situations said how '{top['label']}' turned out, so this rests on advice only.")
        if n_sit < C.LOW_CONF_MIN_SITUATIONS or top_out < C.LOW_CONF_MIN_OUTCOMES:
            conf = "low"
            warn.append(f"Low confidence: {n_sit} similar situations and {top_out} outcome reports for this option "
                        f"(needs {C.LOW_CONF_MIN_SITUATIONS}+ and {C.LOW_CONF_MIN_OUTCOMES}+).")
        elif n_sit >= C.HIGH_CONF_MIN_SITUATIONS and top_out >= C.HIGH_CONF_MIN_OUTCOMES and share >= C.HIGH_CONF_MIN_SHARE:
            conf = "high"
        else:
            conf = "medium"
        t = top["outcomes"]
        why = (f"Highest net support ({top['net']:.2f}) across {n_sit} similar situations: {top['advice']['recommends']} advice "
               f"comments for it, {top['advice']['opposes']} against, and {t['good']} good / {t['bad']} bad / {t['mixed']} mixed "
               f"outcomes from people who chose it. It holds {share:.0%} of all positive net support.")
        v["recommendation"] = {"option": top["option"], "label": top["label"], "confidence": conf, "why": why}

        # 4. dissent: a strong rival option, or heavy pushback on the winner
        rival = next((r for r in main[1:] if r["support"] > 0), None)
        d = q = None
        if rival and rival["support"] >= C.DISSENT_MIN_RATIO * top["support"]:
            d = {"kind": "rival_option", "option": rival["option"], "label": rival["label"],
                 "strength": round(rival["support"] / top["support"], 2)}
            q = best.get((rival["option"], 1))
        elif top["against"] >= C.DISSENT_MIN_RATIO * top["support"]:
            d = {"kind": "pushback", "option": top["option"], "label": f"pushback on '{top['label']}'",
                 "strength": round(top["against"] / top["support"], 2)}
            q = best.get((top["option"], -1))
        if d:
            d["example"] = _quote(kg, q[1]) if q else None
            d["direct_disagreements"] = _disagreements(kg, advice_ids, top["option"])
            v["dissent"] = d

    # tactics go with any decision, so they are listed as tips instead of competing with the decisions
    for r in scores:
        if r["option"] in C.TACTICS and r["advice"]["recommends"] >= C.TIP_MIN_ADVICE and r["support"] > r["against"]:
            q = best.get((r["option"], 1))
            v["tips"].append({"option": r["option"], "label": r["label"], "advice_for": r["advice"]["recommends"],
                              "advice_against": r["advice"]["opposes"], "support": r["support"],
                              "example": _quote(kg, q[1]) if q else None})

    # 5. what happened to similar people
    known = [x for x in shown if kg.nodes[x[2]]["polarity"] != "unknown"]   # unknown polarity tells the user nothing
    for w, sim, oid in sorted(known, reverse=True)[:6]:
        o = kg.nodes[oid]
        sid, props = kg.edges(oid, "FROM")[0]
        v["outcomes"].append({"option": o["chose"], "label": C.OPTIONS[o["chose"]], "counts_for": remap_out.get(o["chose"], o["chose"]),
                              "polarity": o["polarity"], "year": o["created"][:4],
                              "similarity": round(sim, 2), "situation": brief(kg.nodes[sid]),
                              "situation_inherited": bool(props.get("inherited")), "author": o.get("author"),
                              "snippet": o["snippet"], "url": o["url"]})

    # 6. risk flags: factors common in bad outcomes but rare in advice
    bad = [oid for _, oid in outcomes if kg.nodes[oid]["polarity"] == "bad"]
    scope, adv = "similar situations", advice_ids
    if len(bad) < C.RISK_MIN_BAD_OUTCOMES:
        scope = "whole graph"
        bad = [oid for oid in kg.by_type["Outcome"] if kg.nodes[oid]["polarity"] == "bad"]
        adv = kg.by_type["Advice"]
    if bad and adv:
        for f, label in C.FACTORS.items():
            hits = [oid for oid in bad if f in kg.factors.get(oid, ())]
            bad_share = len(hits) / len(bad)
            adv_share = sum(1 for aid in adv if f in kg.factors.get(aid, ())) / len(adv)
            if bad_share >= C.RISK_MIN_BAD_SHARE and adv_share < C.RISK_MAX_ADVICE_SHARE:
                after = Counter(kg.nodes[oid]["chose"] for oid in hits).most_common(1)[0][0]
                v["risk_flags"].append({"factor": f, "label": label, "bad_outcome_share": round(bad_share, 2),
                                        "advice_share": round(adv_share, 3), "bad_outcomes": len(hits), "scope": scope,
                                        "mostly_after": after})
        v["risk_flags"].sort(key=lambda x: x["bad_outcome_share"], reverse=True)

    # 7. who to listen to
    ranked = []
    for name, voice in voices.items():
        node = kg.nodes.get(f"u:{name}", {})
        lean = max(voice["lean"].items(), key=lambda kv: abs(kv[1]))[0] if voice["lean"] else None
        ranked.append({"author": name, "credibility": node.get("credibility", 0.0),
                       "parts": {k: node.get(k) for k in ("lived", "outcomes", "upvotes", "network")},
                       "evidence_weight": round(voice["weight"], 3),
                       "leans": (("for: " if voice["lean"][lean] > 0 else "against: ") + C.OPTIONS[lean]) if lean else None,
                       "url": voice["url"]})
    ranked.sort(key=lambda r: (r["credibility"], r["evidence_weight"]), reverse=True)
    v["credible_voices"] = ranked[:5]

    total = sum(era_mass.values())
    if total and era_mass.get("boom", 0) / total > 0.5:
        warn.append(f"{era_mass['boom'] / total:.0%} of the matched evidence is from the 2021-22 hiring boom, when switching was easier.")
    return v
