"""Free text -> Situation: company type, experience, salary, notice period, city.
These rules plus lexicon.py are the whole extractor."""

import re

from . import lexicon as L


def _alt(parts):
    return "|".join(f"(?:{p})" for p in parts)


_GEN = dict(L.GENERIC_TIERS)
_SERVICE_ALIASES = [a for tier, al in L.COMPANIES.values() if tier == "service" for a in al]
_PRODUCT_ALIASES = [a for tier, al in L.COMPANIES.values() if tier != "service" for a in al]
SERVICE_SRC = _alt(_SERVICE_ALIASES + [_GEN["service"]])
PRODUCT_SRC = _alt(_PRODUCT_ALIASES + [_GEN["product"], _GEN["startup"]])
ANYCO_SRC = _alt(_SERVICE_ALIASES + _PRODUCT_ALIASES)


def fill(pattern):
    return pattern.replace("{SERVICE}", SERVICE_SRC).replace("{PRODUCT}", PRODUCT_SRC).replace("{ANYCO}", ANYCO_SRC)


def rx(pattern):
    return re.compile(fill(pattern), re.I)


_CHARS = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', " ": " ", "₹": "rs "})


def normalize_text(text):
    text = (text or "").translate(_CHARS)
    return text.replace("&amp;", "&").replace("&gt;", ">").replace("&lt;", "<")


_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")
_FIRST_PERSON = re.compile(r"\b(?:i|i'm|im|i've|ive|i'd|my|me|we|our)\b", re.I)


def split_sentences(text):
    return [s.strip() for s in _SENT_SPLIT.split(text or "") if s and s.strip()]


# ---------- companies ----------
_COMPANY_RX = [(name, tier, re.compile(r"\b(?:" + _alt(al) + r")\b", re.I)) for name, (tier, al) in L.COMPANIES.items()]
_GENERIC_RX = [(tier, re.compile(r"\b(?:" + src + r")\b", re.I)) for tier, src in L.GENERIC_TIERS]


def find_companies(text):
    hits = [(m.start(), m.end(), name, tier) for name, tier, r in _COMPANY_RX for m in r.finditer(text)]
    hits += [(m.start(), m.end(), None, tier) for tier, r in _GENERIC_RX for m in r.finditer(text)]
    hits.sort(key=lambda h: (h[0], h[0] - h[1]))
    kept, end = [], -1
    for h in hits:
        if h[0] >= end:
            kept.append(h)
            end = h[1]
    return kept


# ---------- money, always converted to LPA ----------
def _num(s):
    return float(s.replace(",", ""))


def _rupees(m):
    v = _num(m.group(1))
    if m.group(2):
        return v * 12 / 1e5 if v >= 5000 else None
    return v / 1e5 if v >= 1e5 else None


_N = r"(\d+(?:\.\d+)?)"
_MONEY = [
    (re.compile(_N + r"\s*(?:lpa|l\.p\.a\.?|lakhs?|lacs?|lakh|lac|lks?|l)\b", re.I), lambda m: _num(m.group(1))),
    (re.compile(_N + r"\s*(?:cr|crores?)\b", re.I), lambda m: _num(m.group(1)) * 100),
    (re.compile(_N + r"\s*k\b\.?\s*(?:per month|/\s*month|/\s*m\b|pm\b|p\.m\.|a month|monthly|in[- ]?hand)", re.I),
     lambda m: _num(m.group(1)) * 12 / 100),
    (re.compile(r"\b(?:rs\.?|inr)\s*(\d{1,3}(?:,\d{2,3})+|\d{5,8})\b(\s*(?:per month|/\s*month|pm\b|monthly|a month))?", re.I), _rupees),
    (re.compile(r"\b(?:ctc|package|salary)\s*(?:of|is|was|:|-|=|~|around|about|approx\.?)?\s*(?:rs\.?|inr)?\s*(\d{1,3}(?:\.\d+)?)\b"
                r"(?!\s*(?:k\b|%|\+|yoe|years?|yrs?|months?|days?|lpa|l\b|lakhs?|lacs?|lac\b|cr\b|crores?|,\d))", re.I),
     lambda m: _num(m.group(1))),
]


def find_money(text):
    found, taken = [], []
    for r, conv in _MONEY:
        for m in r.finditer(text):
            if any(m.start() < e and s < m.end() for s, e in taken):
                continue
            try:
                v = conv(m)
            except ValueError:
                v = None
            if v is None or not 1.0 <= v <= 300.0:
                continue
            taken.append((m.start(), m.end()))
            found.append((m.start(), m.end(), round(v, 2)))
    return sorted(found)


# ---------- which side of the decision a mention belongs to ----------
_MONEY_OFFER_CUE = re.compile(r"\b(?:offers?|offered|offering|new|getting|got|giving|expected|expecting|ectc|selected|joining)\b", re.I)
_MONEY_CURRENT_CUE = re.compile(r"\b(?:current|currently|cctc|drawing|earning|earn|making|paid|present|existing|my ctc|my salary|my package|i get|i'?m on|i am on)\b", re.I)
_CO_OFFER_CUE = re.compile(
    r"\b(?:offers?(?: letter)?(?: from| by| at| in| of)?|offered(?: by| at| from)?|got (?:an? |the )?(?:offer|call|job)(?: from| at| in| with)?"
    r"|selected(?: in| at| by| for| with)?|cleared(?: the)?(?: interviews?)?(?: of| at| for)?|join(?:ing)?|switch(?:ing)? to|mov(?:e|ing) to"
    r"|go(?:ing)? to|new (?:company|job|org)|placed (?:in|at)|onboarding(?: at| in| with)?|vs\.?|or|to)\b", re.I)
_CO_CURRENT_CUE = re.compile(
    r"\b(?:work(?:ing|ed)? (?:at|in|for|with)|currently(?: at| in| with| working(?: at| in| for| with)?)?"
    r"|i(?:'m| am| was) (?:at|in|with|working (?:at|in|for|with))|employed (?:at|in|by|with)|been (?:at|in|with)|job (?:at|in)"
    r"|stuck (?:at|in)|joined|started (?:at|in|with)|from|leav(?:e|ing)|left|quit(?:ting)?|resign(?:ing|ed)?(?: from)?|my (?:current )?(?:company|org|employer)(?: is)?)\b", re.I)
_POST_OFFER = re.compile(r"\s*(?:[a-z]+\s+){0,2}offer\b", re.I)
_ADJ_FROM = re.compile(r"\bfrom\s*$", re.I)
_ADJ_TO = re.compile(r"\bto\s*$", re.I)
_BOUNDARY = re.compile(r"[.!?](?=\s)|\n")


def _role(text, start, end, offer_cue, current_cue, window=50, adjacency=False):
    """Nearest cue word before a mention decides if it is the current side or the offer side."""
    pre = text[max(0, start - window):start]
    cut = None
    for cut in _BOUNDARY.finditer(pre):     # cue words only count inside the same sentence
        pass
    if cut:
        pre = pre[cut.end():]
    if adjacency:
        if _ADJ_FROM.search(pre):
            return "current"
        if _ADJ_TO.search(pre):
            return "offer"
    best, role = None, None
    for name, cue in (("offer", offer_cue), ("current", current_cue)):
        for m in cue.finditer(pre):
            d = len(pre) - m.end()
            if best is None or d < best:
                best, role = d, name
    if _POST_OFFER.match(text, end) and (best is None or best > 2):
        role = "offer"
    return role


def _assign_money(text, has_offer, stage):
    cur = off = None
    loose = []
    for s, e, v in find_money(text):
        r = _role(text, s, e, _MONEY_OFFER_CUE, _MONEY_CURRENT_CUE, adjacency=True)
        if r == "current":
            cur = v if cur is None else cur
        elif r == "offer":
            off = v if off is None else off
        else:
            loose.append(v)
    if cur is None and off is None and len(loose) >= 2:
        cur, off = min(loose[:2]), max(loose[:2])          # "4.5 to 11" style, no cue words
    elif loose:
        v = loose[0]
        if cur is None and off is None:
            if has_offer and stage != "employed":
                off = v
            else:
                cur = v
        elif cur is None and v < off:
            cur = v
        elif off is None and v > cur:
            off = v
    return cur, off


def _assign_companies(text, stage):
    cur = tgt = None
    loose = []
    for s, e, name, tier in find_companies(text):
        item = (name, tier)
        r = _role(text, s, e, _CO_OFFER_CUE, _CO_CURRENT_CUE, window=40)
        if r == "current":
            cur = cur or item
        elif r == "offer":
            if tgt is None and item != cur:
                tgt = item
        else:
            loose.append(item)
    for item in loose:
        if cur is None and stage == "employed" and item[1] == "service":
            cur = item
        elif tgt is None and item != cur and (item[1] != "service" or stage != "employed"):
            tgt = item
    if cur and tgt and cur == tgt:
        tgt = None
    return cur, tgt


# ---------- experience, notice, city ----------
_NUMWORDS = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}
_NW = r"(\d+(?:\.\d+)?|one|two|three|four|five|six|seven|eight|nine|ten|an?)"
_YOE_RX = [
    re.compile(r"\b" + _NW + r"\s*\+?\s*(?:yoe\b|y\.o\.e|(?:years?|yrs?)\s+(?:of\s+)?(?:work\s+|industry\s+|total\s+|professional\s+|relevant\s+|it\s+)?(?:exp\b|exp\.|experience))", re.I),
    rx(r"\b(?:working|worked|been|employed|stuck)\b[^.!?\n]{0,40}?\bfor\s+(?:the\s+)?(?:last\s+|past\s+)?" + _NW + r"\s*(?:years?|yrs?)\b"),
    rx(r"\b" + _NW + r"\s*(?:years?|yrs?)\s+(?:at|in|with)\s+(?:{ANYCO}|my (?:current )?(?:company|org)|(?:a|an|the) (?:service|product|mnc|startup))"),
]
_MONTHS_RX = re.compile(r"\b(\d{1,2})\s*(?:months?|mos)\s+(?:of\s+)?(?:exp\b|experience|at\b|in\b|into\b|with\b)", re.I)
_FRESHER_RX = re.compile(
    r"\b(?:fresher|freshers|final[- ]year|pre[- ]final|college student|campus placements?|on[- ]campus|off[- ]campus|passed out"
    r"|pass[- ]?out|graduating|just graduated|new grad|recent grad(?:uate)?|20[12]\d (?:grad|graduate|batch|pass ?out))\b", re.I)
_EMPLOYED_RX = re.compile(
    r"\b(?:my (?:current )?(?:company|manager|team|org|employer|project|ctc|appraisal)|working (?:at|in|for|with)"
    r"|currently (?:at|in|with|working)|i(?:'m| am) (?:at|in|with) |on (?:the )?bench|notice period)\b", re.I)
_OFFER_RX = re.compile(r"\b(?:offers?|offered|offer letter|selected|got (?:an? |the )?(?:job|call|offer)|loi|onboarding)\b", re.I)
_NO_OFFER_RX = re.compile(r"\b(?:no|without|zero|don'?t have (?:an?|any)|do not have (?:an?|any)|haven'?t (?:got|received) (?:an?|any))\s+offers?\b", re.I)
_NOTICE_RX = [
    (re.compile(r"\b(\d{2,3})\s*-?\s*days?\s+(?:of\s+)?notice", re.I), 1),
    (re.compile(r"\bnotice(?:\s+period)?\s*(?:of|is|was|:|-|=)?\s*(\d{1,3})\s*(?:-\s*)?(days?|months?)\b", re.I), 0),
    (re.compile(r"\b(\d|one|two|three)\s*-?\s*months?\s+(?:of\s+)?notice", re.I), 30),
]
_CITY_RX = [(name, re.compile(r"\b(?:" + _alt(al) + r")\b", re.I)) for name, al in L.CITIES.items()]


def _to_num(s):
    s = s.lower()
    return float(_NUMWORDS[s]) if s in _NUMWORDS else float(s)


def find_yoe(text):
    for r in _YOE_RX:
        m = r.search(text)
        if m:
            v = _to_num(m.group(1))
            if 0 <= v <= 30:
                return v
    m = _MONTHS_RX.search(text)
    if m and int(m.group(1)) <= 36:
        return round(int(m.group(1)) / 12, 2)
    return None


def find_notice(text):
    for r, mult in _NOTICE_RX:
        m = r.search(text)
        if not m:
            continue
        if mult == 0:
            v = int(m.group(1))
            return v * 30 if m.group(2).lower().startswith("month") else v
        return int(_to_num(m.group(1)) * mult)
    return None


def find_city(text):
    best = None
    for name, r in _CITY_RX:
        m = r.search(text)
        if m and (best is None or m.start() < best[0]):
            best = (m.start(), name)
    return best[1] if best else None


FIELDS = ("current_tier", "target_tier", "yoe", "current_ctc", "offer_ctc", "notice_days", "city")


def extract_situation(text, first_person_only=False):
    """first_person_only: keep only sentences where the writer talks about themselves (used on comments)."""
    text = normalize_text(text)
    if first_person_only:
        text = " ".join(s for s in split_sentences(text) if _FIRST_PERSON.search(s))
    yoe = find_yoe(text)
    if _FRESHER_RX.search(text) and (yoe is None or yoe < 1):
        stage, yoe = "fresher", (0.0 if yoe is None else yoe)
    elif _EMPLOYED_RX.search(text) or (yoe is not None and yoe > 0):
        stage = "employed"
    else:
        stage = None
    has_offer = bool(_OFFER_RX.search(text)) and not _NO_OFFER_RX.search(text)
    cur, tgt = _assign_companies(text, stage)
    if stage is None and cur:
        stage = "employed"
    cur_ctc, off_ctc = _assign_money(text, has_offer, stage)
    sit = {
        "current_company": cur[0] if cur else None,
        "current_tier": cur[1] if cur else ("fresher" if stage == "fresher" else None),
        "target_company": tgt[0] if tgt else None,
        "target_tier": tgt[1] if tgt else None,
        "yoe": yoe,
        "current_ctc": cur_ctc,
        "offer_ctc": off_ctc,
        "notice_days": find_notice(text),
        "city": find_city(text),
        "has_offer": has_offer,
        "stage": stage,
    }
    sit["fields"] = [f for f in FIELDS if sit[f] is not None]
    return sit


def has_core(sit):
    return bool(sit) and (sit.get("current_tier") is not None or sit.get("yoe") is not None)


# ---------- theme filter used when selecting threads ----------
_THEME_EXPLICIT = re.compile(
    r"service\W+(?:based\W+)?(?:compan(?:y|ies)\W+)?(?:vs\.?|or|to|versus)\W+product"
    r"|product\W+(?:based\W+)?(?:compan(?:y|ies)\W+)?(?:vs\.?|or|versus)\W+service", re.I)
_THEME_SERVICE = rx(r"\b(?:{SERVICE})\b")
_JOB_MOVE = rx(L.JOB_MOVE)
_TIER_WORDS = re.compile(L.TIER_WORDS, re.I)
_PREFILTER = rx(r"\b(?:{SERVICE}|{PRODUCT}|offers?|switch(?:ing)?|join(?:ing)?|fresher|confused|dilemma|advice|suggest(?:ion)?s?"
                r"|should i|career|mnc|package|ctc|lpa|hike|resign|quit|leave|leaving)\b")


def title_prefilter(title):
    return bool(_PREFILTER.search(normalize_text(title)))


def is_on_theme(title, body):
    """Service vs product decision threads: an explicit "service vs product", or a service company plus a
    job-move word in the title. Vague titles ("need advice") pass only if one body sentence has both."""
    title, body = normalize_text(title), normalize_text(body)
    if _THEME_EXPLICIT.search(f"{title}\n{body}"):
        return True
    if not _THEME_SERVICE.search(f"{title}\n{body}"):
        return False
    if _JOB_MOVE.search(title) or _TIER_WORDS.search(title):
        return True
    return any(_THEME_SERVICE.search(s) and _JOB_MOVE.search(s) for s in split_sentences(body))


def experience_situation(title):
    """In an experience thread the commenters were not in the asker's spot. All we know is that the thread is
    about working at a service company, so that is the only thing a story without its own details inherits."""
    hit = next((h for h in find_companies(normalize_text(title)) if h[3] == "service"), None)
    sit = {f: None for f in ("target_company", "target_tier", "yoe", "current_ctc", "offer_ctc", "notice_days", "city")}
    sit.update(current_company=hit[2] if hit else None, current_tier="service", has_offer=False, stage="employed")
    sit["fields"] = ["current_tier"]
    return sit


def thread_role(title, body):
    """'decision': someone weighing the choice (gives questions, advice and outcomes).
    'experience': a service company in the title but no decision, e.g. "Infosys is firing employees".
    People share what happened to them there, so these threads give outcome stories only."""
    if is_on_theme(title, body):
        return "decision"
    if _THEME_SERVICE.search(normalize_text(title)):
        return "experience"
    return None
