"""Downloads the data subset from the Arctic Shift archive in resumable stages.
Stop it any time with Ctrl+C; running the same command again continues where it stopped.

Why it pages through the listing day by day: in testing, the archive's title search timed out even
on one-month windows, while listing one day of posts worked reliably. So the listing works as the
search: each title is checked against the topic pre-filter as it comes in, and only matching posts
are kept. Nothing else is stored."""

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from . import config as C
from .build import read_jsonl
from .extract import thread_role, title_prefilter

LIST_FIELDS = "id,title,author,created_utc,score,num_comments,link_flair_text"
BODY_FIELDS = "id,title,selftext,author,created_utc,score,num_comments,link_flair_text"
COMMENT_FIELDS = "id,author,body,parent_id,link_id,score,created_utc"


class Client:
    def __init__(self, gap=C.REQUEST_GAP_SECONDS):
        self.gap, self.last, self.requests = gap, 0.0, 0

    def get(self, path, **params):
        """Returns the data list, or None after all retries failed."""
        url = f"{C.API_BASE}{path}?{urllib.parse.urlencode(params)}"
        for wait in [0] + C.RETRY_WAITS:
            time.sleep(max(wait, self.gap - (time.time() - self.last)))
            self.last = time.time()
            self.requests += 1
            try:
                req = urllib.request.Request(url, headers={"User-Agent": C.USER_AGENT})
                with urllib.request.urlopen(req, timeout=90) as r:
                    payload = json.loads(r.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                if e.code in (422, 429, 500, 502, 503, 504):   # 422 is how the API says "slow down"
                    continue
                raise
            except (urllib.error.URLError, TimeoutError, ConnectionError, OSError, json.JSONDecodeError):
                continue
            if payload.get("error"):
                continue
            return payload.get("data") or []
        return None


def _epoch(d):
    return int(datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp())


def _load(path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def _save(path, obj):
    path.write_text(json.dumps(obj, indent=1), encoding="utf-8")


def _fmt(seconds):
    m = int(seconds // 60)
    return f"{m // 60}h {m % 60:02d}m" if m >= 60 else f"{m}m {int(seconds % 60):02d}s"


def _paginate(client, path, params, cursor):
    """Walks a time-sorted endpoint 100 items at a time. Returns items, or None on failure."""
    seen, items = set(), []
    while True:
        query = dict(params, limit=100, sort="asc")
        if cursor is not None:
            query["after"] = cursor
        page = client.get(path, **query)
        if page is None:
            return None
        fresh = [x for x in page if x["id"] not in seen]
        for x in fresh:
            seen.add(x["id"])
            items.append(x)
        if len(page) < 100:
            return items
        last = max(int(x["created_utc"]) for x in page)
        cursor = last - 1 if fresh else last     # "after" is exclusive; step back a second so same-second items are not lost


def is_candidate(p):
    """Topic pre-filter applied while the listing streams in: enough comments, not a bot, on-topic title words."""
    return ((p.get("num_comments") or 0) >= C.LISTING_MIN_COMMENTS and p.get("author") not in C.BOT_AUTHORS
            and title_prefilter(p.get("title")))


def stage_listing(client, raw, since, until, log):
    state_path = raw / "listing_state.json"
    state = _load(state_path, {"done": [], "failed": []})
    done, failed = set(state["done"]), set()
    seen, kept = state.get("seen", 0), state.get("kept", 0)

    def save():
        _save(state_path, {"done": sorted(done), "failed": sorted(failed), "seen": seen, "kept": kept})
    d0, d1 = date.fromisoformat(since), date.fromisoformat(until)
    todo = [d for d in (d0 + timedelta(n) for n in range((d1 - d0).days)) if d.isoformat() not in done]
    log(f"[1/3 listing] {len(todo)} days to list ({since} to {until})")
    t0 = time.time()
    try:
        with open(raw / "listing.jsonl", "a", encoding="utf-8") as out:
            for i, d in enumerate(todo, 1):
                items = _paginate(client, "/api/posts/search",
                                  {"subreddit": C.SUBREDDIT, "before": _epoch(d + timedelta(1)), "fields": LIST_FIELDS}, _epoch(d) - 1)
                if items is None:
                    failed.add(d.isoformat())
                else:
                    keep = [p for p in items if is_candidate(p)]
                    for p in keep:
                        out.write(json.dumps(p, ensure_ascii=False) + "\n")
                    seen, kept = seen + len(items), kept + len(keep)
                    done.add(d.isoformat())
                    failed.discard(d.isoformat())
                if i % 10 == 0 or i == len(todo):
                    out.flush()
                    save()
                    left = (time.time() - t0) / i * (len(todo) - i)
                    log(f"[1/3 listing] {d.isoformat()} | {i}/{len(todo)} days | {seen} posts seen, {kept} kept | ~{_fmt(left)} left")
    finally:
        save()
    if failed:
        log(f"[1/3 listing] {len(failed)} days failed after retries. Run fetch again to retry them.")


def stage_bodies(client, raw, log):
    listing = read_jsonl(raw / "listing.jsonl")
    candidates = [p for p in listing.values() if is_candidate(p)]
    have = read_jsonl(raw / "posts.jsonl")
    todo = [p["id"] for p in candidates if p["id"] not in have]
    log(f"[2/3 bodies] {len(candidates)} on-topic titles kept from the listing, {len(todo)} bodies to fetch")
    with open(raw / "posts.jsonl", "a", encoding="utf-8") as out:
        for i in range(0, len(todo), 100):
            page = client.get("/api/posts/ids", ids=",".join(todo[i:i + 100]), fields=BODY_FIELDS)
            if page is None:
                log(f"[2/3 bodies] batch {i // 100 + 1} failed, it will be retried on the next run")
                continue
            for p in page:
                out.write(json.dumps(p, ensure_ascii=False) + "\n")
            out.flush()
            if (i // 100 + 1) % 10 == 0:
                log(f"[2/3 bodies] {min(i + 100, len(todo))}/{len(todo)}")


def stage_select(raw, max_threads, log):
    posts = read_jsonl(raw / "posts.jsonl")
    ranked = sorted(posts.values(), key=lambda p: p.get("num_comments") or 0, reverse=True)
    roles = {p["id"]: thread_role(p.get("title"), p.get("selftext")) for p in ranked}
    decision = [p["id"] for p in ranked if roles[p["id"]] == "decision"]
    experience = [p["id"] for p in ranked if roles[p["id"]] == "experience"]
    chosen = decision[:max_threads] + experience[:C.EXPERIENCE_FETCH]
    _save(raw / "selected.json", {"rule": "extract.thread_role on title + body, most comments first",
                                  "posts_checked": len(posts), "decision": len(decision), "experience": len(experience),
                                  "ids": chosen})
    log(f"[2/3 select] {len(decision)} decision and {len(experience)} experience threads found in {len(posts)} posts; "
        f"keeping {min(len(decision), max_threads)} + {min(len(experience), C.EXPERIENCE_FETCH)} most discussed")


def stage_comments(client, raw, log):
    sel = raw / "selected.json"
    if not sel.exists():
        log("[3/3 comments] selected.json missing. Run the listing and bodies stages first.")
        return
    ids = json.loads(sel.read_text(encoding="utf-8"))["ids"]
    todo = [pid for pid in ids if not (raw / "comments" / f"{pid}.json").exists()]
    log(f"[3/3 comments] {len(todo)} of {len(ids)} threads still need comments")
    t0 = time.time()
    for i, pid in enumerate(todo, 1):
        items = _paginate(client, "/api/comments/search", {"link_id": pid, "fields": COMMENT_FIELDS}, None)
        if items is None:
            log(f"[3/3 comments] {pid} failed, it will be retried on the next run")
            continue
        (raw / "comments" / f"{pid}.json").write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")
        if i % 20 == 0 or i == len(todo):
            log(f"[3/3 comments] {i}/{len(todo)} threads | ~{_fmt((time.time() - t0) / i * (len(todo) - i))} left")


def run(stage="all", since=C.DATE_FROM, until=None, max_threads=C.FETCH_COMMENTS_FOR, raw_dir=C.RAW_DIR, log=print):
    raw = Path(raw_dir)
    (raw / "comments").mkdir(parents=True, exist_ok=True)
    until = until or date.today().isoformat()
    client, t0 = Client(), time.time()
    try:
        if stage in ("all", "listing"):
            stage_listing(client, raw, since, until, log)
        if stage in ("all", "bodies"):
            stage_bodies(client, raw, log)
            stage_select(raw, max_threads, log)
        if stage in ("all", "comments"):
            stage_comments(client, raw, log)
    except KeyboardInterrupt:
        log("Stopped. Progress is saved; run the same command again to continue.")
    log(f"Finished in {_fmt(time.time() - t0)} with {client.requests} API requests.")
