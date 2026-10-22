"""Every tunable decision lives here, next to the reason for it.
Change a value, run `python cli.py build`, and the graph and answers follow."""

from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
STATE_DIR = ROOT / "knowledge_state"
OUTPUT_DIR = ROOT / "outputs"
EVAL_DIR = ROOT / "eval"

# ---------------- data subset ----------------
SUBREDDIT = "developersIndia"
DATE_FROM = "2021-01-01"     # covers the 2021-22 hiring boom and the slowdown after it
LISTING_MIN_COMMENTS = 5     # loose first cut: the archive sometimes stores comment counts from early in a thread's life
FETCH_COMMENTS_FOR = 1000    # threads whose full comment lists get downloaded
MIN_COMMENTS = 10            # final cut on real, usable comments: below this there is rarely disagreement or an outcome
MAX_THREADS = 800            # decision threads kept in the graph, most discussed first
EXPERIENCE_FETCH = 250       # experience threads whose comments get downloaded (outcome stories only)
EXPERIENCE_THREADS = 200     # experience threads kept in the graph
BOT_AUTHORS = {"AutoModerator", "devsIndiaBot"}

# ---------------- Arctic Shift API ----------------
API_BASE = "https://arctic-shift.photon-reddit.com"
REQUEST_GAP_SECONDS = 1.5    # faster than this and the API answers "Timeout. Maybe slow down a bit"
RETRY_WAITS = [5, 10, 20, 40, 60]
USER_AGENT = "careergraph/0.1 (personal research project)"

# ---------------- the options ----------------
# 5 decisions the verdict picks from, plus 2 tactics that go with any decision.
# The first version ranked 6 options together. On the full data, negotiate and keep-interviewing won by
# default: nobody argues against them and nobody reports how they went. So they are shown as tips now.
OPTIONS = {
    "accept_service": "Join or stay in the service company",
    "wait_for_product": "Hold out for a product company",
    "switch_now": "Take the product / startup move now",
    "upskill_then_switch": "Stay for now, prepare, switch later",
    "resign_without_offer": "Quit first, then search",
    "negotiate": "Negotiate before you decide",
    "accept_and_keep_interviewing": "Keep interviewing after you join",
}
MAIN_OPTIONS = ("accept_service", "wait_for_product", "switch_now", "upskill_then_switch", "resign_without_offer")
TACTICS = ("negotiate", "accept_and_keep_interviewing")
# where the asker stands decides which decisions fit: a fresher has no job to quit yet, and someone
# already holding a product offer has nothing to hold out for
APPLICABLE = {
    "fresher": ("accept_service", "wait_for_product", "switch_now"),
    "offer_in_hand": ("switch_now", "accept_service", "upskill_then_switch"),
    "employed": ("accept_service", "switch_now", "upskill_then_switch", "resign_without_offer"),
}
# stories are told from the writer's timeline. "Joined TCS, prepared, switched after 2 years" is where a fresher's
# "join the service company" leads, and it is the jump someone holding a product offer is about to make
REMAP_ADVICE = {"fresher": {"upskill_then_switch": "accept_service"}}
REMAP_OUTCOMES = {"fresher": {"upskill_then_switch": "accept_service"},
                  "offer_in_hand": {"upskill_then_switch": "switch_now"}}
# advice for one side of these pairs is pushback on the other side
CONFLICTING_OPTIONS = {
    frozenset(("accept_service", "wait_for_product")),
    frozenset(("switch_now", "upskill_then_switch")),
    frozenset(("switch_now", "accept_service")),
    frozenset(("resign_without_offer", "upskill_then_switch")),
    frozenset(("resign_without_offer", "accept_service")),
}
FACTORS = {
    "pay": "Pay / CTC",
    "learning": "Learning and quality of work",
    "job_security": "Job security / layoffs",
    "wlb": "Work-life balance",
    "notice_period": "Notice period",
    "bond": "Service bond / agreement",
    "bench": "Bench time / project allocation",
    "brand_value": "Brand value on the resume",
}

# ---------------- evidence weights ----------------
TYPE_WEIGHT = {"outcome": 3.0, "advice": 1.0}   # one real outcome counts like three opinions
# credibility scales each piece of evidence between 0.5x and 1x. Used raw (0.05 to 0.9) it made one outcome
# worth ~16 advice comments, because people who report outcomes are by design the most credible authors
CRED_FLOOR = 0.5
CRED_WEIGHTS = {"lived": 0.4, "outcomes": 0.3, "upvotes": 0.2, "network": 0.1}
OUTCOMES_FOR_FULL = 2        # two outcome reports = full marks on that part
UPVOTE_SHRINK_K = 2          # pulls authors with only 1-2 comments toward the middle

# hiring slowed from the second half of 2022, so the timeline splits there
ERAS = [("boom", "2021-01-01", 0.6), ("slowdown", "2022-07-01", 0.8), ("current", "2024-01-01", 1.0)]

# ---------------- matching ----------------
MATCH_WEIGHTS = {"tier": 0.5, "yoe": 0.3, "ctc": 0.2}
TIER_SIMILARITY = {frozenset(("product", "startup")): 0.6, frozenset(("fresher", "service")): 0.3}
YOE_ZERO_AT = 3.0            # 3+ years apart = no experience similarity
CTC_ZERO_RATIO = 2.5         # 2.5x salary gap = no salary similarity (compared on a log scale)
MISSING_FIELD_FLOOR = 0.4    # similarity x (floor + (1 - floor) x share of match weight both sides have)
MIN_SIMILARITY = 0.35
TOP_K_SITUATIONS = 30
MAX_OUTCOMES = 60
INHERITED_SITUATION_DISCOUNT = 0.7   # outcome had no situation of its own, so it borrowed the thread's

# ---------------- verdict rules ----------------
LOW_CONF_MIN_SITUATIONS = 5
LOW_CONF_MIN_OUTCOMES = 2
HIGH_CONF_MIN_SITUATIONS = 15
HIGH_CONF_MIN_OUTCOMES = 5
HIGH_CONF_MIN_SHARE = 0.5
DISSENT_MIN_RATIO = 0.4
RISK_MIN_BAD_SHARE = 0.30
RISK_MAX_ADVICE_SHARE = 0.10
RISK_MIN_BAD_OUTCOMES = 3
TIP_MIN_ADVICE = 2           # a tactic shows up as a tip when at least this many matched advice comments suggest it
MONEY_GROWTH_RATIO = 1.5     # a story where pay grew 1.5x or more counts as a good outcome

SNIPPET_CHARS = 280


def iso_date(ts):
    return datetime.fromtimestamp(int(ts), tz=timezone.utc).date().isoformat()


def era_of(date_str):
    name, weight = ERAS[0][0], ERAS[0][2]
    for era, start, w in ERAS:
        if date_str >= start:
            name, weight = era, w
    return name, weight


def snippet(text, n=SNIPPET_CHARS):
    t = " ".join((text or "").split())
    return t if len(t) <= n else t[: n - 3].rstrip() + "..."


def post_url(pid):
    return f"https://www.reddit.com/r/{SUBREDDIT}/comments/{pid}/"


def comment_url(pid, cid):
    return f"https://www.reddit.com/r/{SUBREDDIT}/comments/{pid}/_/{cid}/"
