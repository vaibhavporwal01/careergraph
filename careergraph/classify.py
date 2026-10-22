"""Labels a comment as advice / outcome / noise and pulls out what it says:
which option it pushes or argues against, which factors it cites,
what the writer chose and how it went."""

import re

from . import config as C
from . import lexicon as L
from .extract import _alt, extract_situation, find_money, has_core, normalize_text, rx, split_sentences

_ADVICE_RX = [rx(p) for p in L.ADVICE_MARKERS]
_IMPERATIVE_RX = rx(L.IMPERATIVE_START)
_OPTION_RX = [(rx(p), opt) for p, opt in L.OPTION_CUES]
_FIXED_RX = [(rx(p), opt, st) for p, opt, st in L.FIXED_CUES]
_GENERIC_ACCEPT_RX = rx(L.GENERIC_ACCEPT)
_NEG_BEFORE_RX = re.compile(L.NEGATION_BEFORE, re.I)
_DECISION_RX = rx(L.OUTCOME_DECISION)
_RESULT_RX = rx(_alt(L.OUTCOME_RESULT))
_CHOICE_RX = [(rx(p), opt) for p, opt in L.CHOICE_RULES]
_NEGATED_POS_RX = [rx(p) for p in L.NEGATED_POSITIVE]
_POS_RX = [rx(p) for p in L.POSITIVE_OUTCOME]
_NEG_RX = [rx(p) for p in L.NEGATIVE_OUTCOME]
_FACTOR_RX = {f: rx(_alt(ps)) for f, ps in L.FACTOR_CUES.items()}
_DISAGREE_RX = rx(_alt(L.DISAGREE_MARKERS))
_AGREE_RX = rx(_alt(L.AGREE_MARKERS))
_EXPERIENCE_RX = rx(_alt(L.EXPERIENCE_MARKERS))
_SWITCH_WORDS = re.compile(r"\b(?:switched|left|quit|resigned|moved)\b", re.I)
_DIRECTIVE_RX = [rx(p) for p in L.DIRECTIVE_MARKERS]
_HYPOTHETICAL_RX = re.compile(L.HYPOTHETICAL, re.I)
_REASON_RX = re.compile(L.REASON_CLAUSE, re.I)
_OTHER_PERSON_RX = re.compile(L.OTHER_PERSON, re.I)
_DID_IT_RX = rx(L.DID_IT)
_LATER_MOVE_RX = rx(L.LATER_MOVE)
_GROWTH_CUE_RX = re.compile(L.GROWTH_CUE, re.I)
_NOT_GROWTH_RX = re.compile(L.NOT_GROWTH, re.I)
_REPORTED_RX = re.compile(L.REPORTED_SPEECH, re.I)
_OTHERS_RX = re.compile(L.OTHERS_CLAUSE, re.I)
_NEGATED_NEG_RX = [rx(p) for p in L.NEGATED_NEGATIVE]


def _own(text):
    """Only the writer's part of a sentence: drops what others said and what other people did."""
    return _OTHERS_RX.sub(" ", _REPORTED_RX.sub(" ", text))


def clean(text):
    text = normalize_text(text)
    text = "\n".join(ln for ln in text.splitlines() if not ln.lstrip().startswith(">"))   # drop quoted lines
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)                                  # markdown links -> text
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"[*_~`#]+", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def _negated(sentence, start):
    return bool(_NEG_BEFORE_RX.search(sentence[max(0, start - 30):start]))


def _resolve_generic(ctx):
    tier = (ctx or {}).get("target_tier")
    if tier == "service":
        return "accept_service"
    if tier in ("product", "startup"):
        return "switch_now"
    return None


def _resolve_decline(ctx):
    tier = (ctx or {}).get("target_tier")
    if tier == "service":
        return "wait_for_product"
    if tier in ("product", "startup"):
        return "accept_service"
    return None


def _is_directive(sentence):
    return bool(_IMPERATIVE_RX.search(sentence) or any(r.search(sentence) for r in _ADVICE_RX)
                or any(r.search(sentence) for r in _DIRECTIVE_RX))


def detect_stances(sentences, ctx):
    """Option -> +1 (recommends) or -1 (opposes). First-person stories are skipped: they are outcomes, not advice."""
    total = {}
    for s in sentences:
        if _DECISION_RX.search(s):
            continue
        found = {(opt, st) for r, opt, st in _FIXED_RX if r.search(s)}
        if not found and not _is_directive(s):
            continue                          # describing something is not recommending it
        fixed = {opt for opt, _ in found}
        for r, opt in _OPTION_RX:
            if opt in fixed:
                continue
            m = r.search(s)
            if m:
                found.add((opt, -1 if _negated(s, m.start()) else 1))
        if not found:
            m = _GENERIC_ACCEPT_RX.search(s)
            opt = _resolve_generic(ctx) if m else None
            if opt:
                found.add((opt, -1 if _negated(s, m.start()) else 1))
        if any(o == "resign_without_offer" for o, _ in found):
            found = {(o, st) for o, st in found if o != "switch_now"}   # "quit TCS and prepare" is quitting first
        for opt, st in found:
            total[opt] = total.get(opt, 0) + st
    return {opt: (1 if v > 0 else -1) for opt, v in total.items() if v}


def _pay_grew(text):
    """The first amount mentioned vs a later one the writer earns (not an offer, not someone else's)."""
    found = find_money(text)
    for start, _, value in found[1:]:
        before = text[max(0, start - 45):start]
        if value >= C.MONEY_GROWTH_RATIO * found[0][2] and _GROWTH_CUE_RX.search(before) and not _NOT_GROWTH_RX.search(before):
            return True
    return False


def outcome_polarity(text, money_text=None):
    masked, pos, neg = text, 0, 0
    for r in _NEGATED_POS_RX:              # "not happy" must not count as happy
        neg += len(r.findall(masked))
        masked = r.sub(" ", masked)
    for r in _POS_RX:                      # "no regrets" must not count as regret
        pos += len(r.findall(masked))
        masked = r.sub(" ", masked)
    for r in _NEGATED_NEG_RX:              # "wasn't on bench" must not count as bench
        masked = r.sub(" ", masked)
    neg += sum(len(r.findall(masked)) for r in _NEG_RX)
    if _pay_grew(money_text if money_text is not None else text):
        pos += 1                           # pay grew to 1.5x or more of the first amount
    if pos and neg:
        return "mixed"
    return "good" if pos else "bad" if neg else "unknown"


def _choice(decision_text, ctx):
    for r, opt in _CHOICE_RX:
        if not r.search(decision_text):
            continue
        if opt in ("GENERIC", "GENERIC_DECLINE"):
            opt = _resolve_generic(ctx) if opt == "GENERIC" else _resolve_decline(ctx)
            if opt is None:
                continue
        # a fresher who went straight to a product company held out for product
        if opt == "switch_now" and (ctx or {}).get("stage") == "fresher" and not _SWITCH_WORDS.search(decision_text):
            opt = "wait_for_product"
        return opt
    return None


def _result_part(sents, first):
    """How it went is told in the decision sentence and after it, minus the reason
    ("because the team was toxic") and minus lines about the reader or other people."""
    s = sents[first]
    head = _own(_REASON_RX.sub(" ", s[_DECISION_RX.search(s).start():]))
    return " ".join([head] + [_own(x) for x in sents[first + 1:] if not _OTHER_PERSON_RX.search(x)])


def _story(sents, decisions):
    """What the writer did: their decision sentences from "I did X" onward, plus the next two sentences
    about themselves ("I quit my job. Been jobless for 8 months" needs the second sentence)."""
    parts = [_own(sents[i][_DECISION_RX.search(sents[i]).start():]).rstrip(".!? ") for i in decisions]
    after = [_own(x).rstrip(".!? ") for x in sents[decisions[0] + 1:] if not _OTHER_PERSON_RX.search(x)][:2]
    return " | ".join(parts + after)


def classify_comment(body, ctx=None):
    """ctx is the Situation of the thread the comment sits in."""
    text = clean(body)
    res = {"text": text, "kind": "noise", "is_advice": False, "is_outcome": False, "stances": {}, "factors": [],
           "outcome": None, "self_situation": None, "experience": False, "reply_hint": None}
    if len(text) < 25:
        return res
    sents = split_sentences(text)
    stances = detect_stances(sents, ctx)
    marker = any(r.search(text) for r in _ADVICE_RX) or any(_IMPERATIVE_RX.search(s) for s in sents)
    res["is_advice"] = bool(marker or stances)
    res["stances"] = stances
    res["factors"] = sorted(f for f, r in _FACTOR_RX.items() if r.search(text))
    own = extract_situation(text, first_person_only=True)
    if has_core(own):
        res["self_situation"] = own
    res["experience"] = bool(_EXPERIENCE_RX.search(text))
    decisions = [i for i, s in enumerate(sents) if _DECISION_RX.search(s) and not _HYPOTHETICAL_RX.search(s)]
    if decisions and _RESULT_RX.search(text):
        # read each story from the writer's own "I did X" onward, so a neighbour's job earlier in the sentence is ignored
        chose = _choice(_story(sents, decisions), ctx)
        rest = _result_part(sents, decisions[0])
        judged = rest
        later = _LATER_MOVE_RX.search(rest) if chose == "accept_service" else None
        if later:
            # joined a service company and later moved to product: stayed, then switched.
            # How it went is judged from the move onward ("bench for 8 months. Now at a startup" is about the move)
            chose, judged = "upskill_then_switch", rest[later.start():]
        if chose:
            res["is_outcome"] = True
            res["outcome"] = {"chose": chose, "polarity": outcome_polarity(judged, money_text=rest),
                              "situation": own if has_core(own) else None}
    if not res["is_outcome"] and len(stances) == 1:
        # "Don't quit your job. I did it and have been jobless for 2 years": the writer did what they advise about
        m = _DID_IT_RX.search(text)
        if m and _RESULT_RX.search(text, m.start()):
            res["is_outcome"] = True
            res["outcome"] = {"chose": next(iter(stances)), "polarity": outcome_polarity(text[m.start():]),
                              "situation": own if has_core(own) else None}
    head = text[:200]
    res["reply_hint"] = "DISAGREES" if _DISAGREE_RX.search(head) else "SUPPORTS" if _AGREE_RX.search(head) else None
    res["kind"] = "outcome" if res["is_outcome"] else "advice" if res["is_advice"] else "noise"
    return res
