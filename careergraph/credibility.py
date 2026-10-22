"""Author credibility = 0.4 lived experience + 0.3 outcome reports + 0.2 thread-normalized upvotes + 0.1 network rank.
Karma alone rewards confident, early, popular comments. This puts weight on people who were in the spot
and said what happened."""

from . import config as C


def pagerank(graph, damping=0.85, iters=60, tol=1e-10):
    """graph: {asker: {helper: weight}}. Written by hand, it is a few lines of power iteration."""
    nodes = set(graph) | {v for outs in graph.values() for v in outs}
    if not nodes:
        return {}
    n = len(nodes)
    rank = {v: 1.0 / n for v in nodes}
    out_w = {u: sum(graph.get(u, {}).values()) for u in nodes}
    for _ in range(iters):
        dangling = sum(rank[u] for u in nodes if out_w[u] == 0)
        new = {v: (1 - damping) / n + damping * dangling / n for v in nodes}
        for u, outs in graph.items():
            if out_w[u]:
                share = damping * rank[u] / out_w[u]
                for v, w in outs.items():
                    new[v] += share * w
        delta = sum(abs(new[v] - rank[v]) for v in nodes)
        rank = new
        if delta < tol:
            break
    return rank


def score_authors(stats, help_edges):
    """stats: {author_id: {pcts, outcomes, self, experience}}; help_edges: who answered whom."""
    pr = pagerank(help_edges)
    top = max(pr.values(), default=0.0) or 1.0
    w, k = C.CRED_WEIGHTS, C.UPVOTE_SHRINK_K
    scores = {}
    for author, s in stats.items():
        lived = 1.0 if s["self"] else (0.5 if s["experience"] else 0.0)
        outcomes = min(1.0, s["outcomes"] / C.OUTCOMES_FOR_FULL)
        n = len(s["pcts"])
        upvotes = (sum(s["pcts"]) + 0.5 * k) / (n + k)
        network = pr.get(author, 0.0) / top
        total = w["lived"] * lived + w["outcomes"] * outcomes + w["upvotes"] * upvotes + w["network"] * network
        scores[author] = {"credibility": round(total, 4), "lived": lived, "outcomes": round(outcomes, 3),
                          "upvotes": round(upvotes, 3), "network": round(network, 3),
                          "comments": n, "outcome_reports": s["outcomes"]}
    return scores
