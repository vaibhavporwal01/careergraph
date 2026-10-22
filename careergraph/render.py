"""Plain-text view of a verdict for the terminal. ASCII only so it prints fine in Windows terminals."""

import textwrap

from . import config as C


def _v(x, unit=""):
    if x is None:
        return "-"
    return f"{x:g}{unit}" if isinstance(x, float) else f"{x}{unit}"


def _who(company, tier):
    return f"{company} ({tier})" if company and tier else (company or tier or "-")


def _wrap(text, indent):
    return textwrap.fill(text, width=100, initial_indent=indent, subsequent_indent=indent)


POSITIONS = {"fresher": "fresher", "offer_in_hand": "holding a product offer", "employed": "employed, no product offer"}


def render(v):
    lines = []
    add = lines.append
    s = v["parsed_situation"]
    add("PARSED SITUATION")
    add(f"  now        {_who(s.get('current_company'), s.get('current_tier'))} | {_v(s.get('yoe'), ' YOE')} | {_v(s.get('current_ctc'), ' LPA')}")
    add(f"  weighing   {_who(s.get('target_company'), s.get('target_tier'))} | offer {_v(s.get('offer_ctc'), ' LPA')} | offer in hand: {'yes' if s.get('has_offer') else 'no'}")
    add(f"  other      notice {_v(s.get('notice_days'), ' days')} | city {_v(s.get('city'))} | position {POSITIONS.get(v.get('position'), '-')}")
    eb = v.get("evidence_base")
    if eb:
        add("")
        add("EVIDENCE USED")
        add(f"  {eb['similar_situations']} similar situations, {eb['advice_comments']} advice comments, {eb['outcome_reports']} outcome reports")
        for t in v.get("matched_threads", [])[:3]:
            add(_wrap(f"- ({t['similarity']}) {t['title']} [{t['situation']}]", "  "))
    rec = v.get("recommendation")
    add("")
    if rec:
        add(f"RECOMMENDATION  [{rec['confidence']} confidence]")
        add(f"  {rec['label']}")
        add(_wrap(rec["why"], "  "))
    else:
        add("RECOMMENDATION")
        add("  none")
    if v.get("tips"):
        add("")
        add("ALSO SUGGESTED  (tips that go with any decision)")
        for t in v["tips"]:
            add(f"  - {t['label']}: {t['advice_for']} advice comments for it, {t['advice_against']} against")
            ex = t.get("example")
            if ex:
                add(_wrap(f"u/{ex['author'] or '[deleted]'} ({ex['year']}): \"{C.snippet(ex['snippet'], 170)}\"", "      "))
    if v.get("option_scores"):
        add("")
        add("DECISION SCORES  (only decisions that fit your position; net = support - pushback)")
        for r in v["option_scores"]:
            a, o = r["advice"], r["outcomes"]
            add(f"  {r['label'][:36]:<36} net {r['net']:>6.2f} | advice +{a['recommends']}/-{a['opposes']} | "
                f"outcomes {o['good']} good, {o['bad']} bad, {o['mixed']} mixed")
    d = v.get("dissent")
    if d:
        add("")
        add(f"MAIN DISSENT  ({d['label']}, strength {d['strength']})")
        ex = d.get("example")
        if ex:
            add(_wrap(f"u/{ex['author'] or '[deleted]'} ({ex['year']}): \"{ex['snippet']}\"", "  "))
            add(f"  {ex['url']}")
        if d.get("direct_disagreements"):
            add(f"  {d['direct_disagreements']} direct replies push back on advice for the recommended option")
    if v.get("outcomes"):
        add("")
        add("WHAT HAPPENED TO PEOPLE IN SIMILAR SPOTS")
        for o in v["outcomes"]:
            moved = f" (counts for '{C.OPTIONS[o['counts_for']]}' in your position)" if o.get("counts_for", o["option"]) != o["option"] else ""
            add(f"  [{o['polarity']}] {o['year']} | {o['situation']} | chose: {o['label']}{moved}")
            add(_wrap(f"\"{o['snippet']}\"", "      "))
            add(f"      {o['url']}")
    if v.get("risk_flags"):
        add("")
        add("RISK FLAGS  (common in bad outcomes, rare in advice)")
        for f in v["risk_flags"]:
            add(_wrap(f"- {f['label']}: in {f['bad_outcome_share']:.0%} of bad outcomes but {f['advice_share']:.0%} of advice "
                      f"({f['scope']}; mostly after '{C.OPTIONS[f['mostly_after']]}')", "  "))
    if v.get("credible_voices"):
        add("")
        add("MOST CREDIBLE VOICES HERE")
        for c in v["credible_voices"]:
            p = c["parts"]
            add(f"  u/{c['author']}  cred {c['credibility']:.2f} (lived {p['lived']}, outcomes {p['outcomes']}, "
                f"upvotes {p['upvotes']}, network {p['network']}) | {c['leans']}")
    if v.get("warnings"):
        add("")
        add("NOTES")
        for w in v["warnings"]:
            add(_wrap(f"- {w}", "  "))
    return "\n".join(lines)
