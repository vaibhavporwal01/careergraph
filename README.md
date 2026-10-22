# CareerGraph

A knowledge graph over r/developersIndia threads about one decision: **service company or product company**. You describe your situation in plain words. It tells you what people in a similar spot were advised, what actually happened to the ones who chose each option, where the advice splits, and which risks people keep underrating.

I built it for the Calyb AI engineering intern assignment (Domain C, community knowledge on Reddit). The reasoning behind every design choice is in [approach.md](approach.md).

## Quick start (no download needed)

The built knowledge base is already in `knowledge_state/`, so you can try it right after cloning:

```
python cli.py ask "5 YOE at Infosys, 12 LPA, got an offer from Amazon for 30 LPA. Should I take it?"
```

Only Python 3.10+ is needed. No packages, no API keys. Downloading and rebuilding the data yourself is optional and described below.

## What it does

1. **Builds a graph** from 1,000 threads (2021 to 2026) with 7 node types (Question, Situation, Option, Advice, Outcome, Factor, Author) and 15 edge types. Entities and relations come from hand-written rules in `careergraph/lexicon.py`, `extract.py` and `classify.py`. No NER library, no LLM.
2. **Takes a new situation** that is not in the data and parses it with the same rules. It works out where the person stands (fresher, holding a product offer, or employed without one), matches them to similar past situations through the graph, and weighs advice and real outcomes by author credibility, market era and similarity.
3. **Returns a structured verdict**: the decision that fits best with a confidence level, tips (negotiate, keep interviewing) when people suggest them, a score per decision, the main dissenting view, outcomes from people in similar spots, risk flags, and the most credible voices. Printed in the terminal and saved as JSON.

## What's in the snapshot

| | |
|---|---|
| Titles checked | 351,054 r/developersIndia titles from 1 Jan 2021 to 20 Oct 2026, checked against the topic filter; 27,693 kept |
| Threads in the graph | 1,000: 800 decision threads, 200 experience threads |
| Comments read | 67,378: 12,309 advice, 267 outcome stories, the rest noise |
| Authors | 7,649 |

Full counts are in `knowledge_state/summary.json`.

## Project structure

```
cli.py                     entry point: fetch, build, ask, stats, label-sample, eval
careergraph/
  config.py                every weight and threshold, with the reason next to it
  lexicon.py               company dictionary and phrase rules (the extraction logic)
  extract.py               text -> Situation (company type, YOE, CTC, notice, city), topic filter
  classify.py              comment -> advice / outcome / noise, stances, factors, what was chosen and how it went
  credibility.py           author credibility, including a hand-written PageRank
  build.py                 raw threads -> graph -> SQLite + JSON + summary
  reason.py                new situation -> position, matching, weighing, verdict
  render.py                readable terminal output
  fetch.py                 resumable download from the Arctic Shift API
  evaluate.py              checks the comment rules against the labels in eval/
knowledge_state/           the built knowledge base (graph.db, knowledge_state.json, summary.json)
eval/                      labeled comments and the eval results (labels.csv, outcome_audit.csv, context.json, results.json)
data/raw/                  downloaded threads (not committed, regenerate with fetch)
examples/                  sample situations to try
tests/                     rule tests and an end-to-end test on synthetic threads
```

## Setup

Python 3.10 or newer. No packages to install, everything is standard library.

```
git clone https://github.com/vaibhavporwal01/careergraph.git
cd careergraph
python --version
```

On Windows, if `python` opens the Microsoft Store, use `py` instead.

## Ask it something

```
python cli.py ask "2 YOE at TCS, 4.5 LPA, got a product startup offer of 12 LPA, 90 days notice"
python cli.py ask --file examples/fresher_service_offer.txt
python cli.py ask --json "1 YOE at Wipro, 3.5 LPA, offer from a product company at 9 LPA"
python cli.py ask
```

The last form prompts for the situation. Mention where you work (or that you are a fresher), your experience, your salary and whether you have an offer. Each verdict is also saved to `outputs/verdict_<timestamp>.json`.

Part of the output for the Infosys to Amazon example above:

```
RECOMMENDATION  [high confidence]
  Take the product / startup move now
  Highest net support (19.09) across 30 similar situations: 30 advice comments for it, 3 against,
  and 5 good / 3 bad / 2 mixed outcomes from people who chose it. It holds 100% of all positive net
  support.

ALSO SUGGESTED  (tips that go with any decision)
  - Negotiate before you decide: 14 advice comments for it, 0 against
  - Keep interviewing after you join: 8 advice comments for it, 0 against

DECISION SCORES  (only decisions that fit your position; net = support - pushback)
  Take the product / startup move now  net  19.09 | advice +30/-3 | outcomes 5 good, 3 bad, 2 mixed
  Stay for now, prepare, switch later  net   0.00 | advice +0/-0 | outcomes 0 good, 0 bad, 0 mixed
  Join or stay in the service company  net  -5.11 | advice +14/-7 | outcomes 5 good, 10 bad, 2 mixed
```

The full output also has the parsed situation, the top matched threads, the main dissent with its strongest comment, what happened to people in similar spots (with links), risk flags, the most credible voices, and notes on missing fields or thin evidence.

## Load or regenerate the knowledge state

The built graph lives in `knowledge_state/`. To rebuild it from scratch:

```
python cli.py fetch
python cli.py build
```

**fetch** pulls r/developersIndia posts from 2021-01-01 to today from the public [Arctic Shift](https://arctic-shift.photon-reddit.com) archive in three stages:

1. Page through the post listing day by day and keep only titles that pass the topic pre-filter. The archive's text search timed out in testing while one-day listings did not, so the listing works as the search and nothing else is stored.
2. Fetch the body of the kept posts, then sort them into decision threads (someone weighing service vs product) and experience threads (a service company in the title, used for outcome stories only).
3. Download all comments for the 1,000 most discussed decision threads and 250 experience threads.

The full range took about 7 hours on my connection because of the pacing the API needs. It is resumable: stop it with Ctrl+C and run the same command again to continue. Raw files go to `data/raw/` (about 60 MB).

For a quick first run on a smaller slice (about 20 minutes):

```
python cli.py fetch --since 2024-01-01 --until 2024-04-01 --max-threads 200
python cli.py build --min-comments 5
```

**build** takes a minute or two. It keeps threads with 10+ usable comments (up to 800 decision and 200 experience threads, most discussed first), builds the graph and writes:

| File | What it is |
|---|---|
| `knowledge_state/summary.json` | Start here. Counts, threads per year, field coverage, stances and outcomes per option, factor mentions, top authors |
| `knowledge_state/knowledge_state.json` | The full graph: `meta`, `schema` (every node and edge type explained), `nodes` grouped by type, `edges`. One item per line so it reads fine in any editor |
| `knowledge_state/graph.db` | The same graph in SQLite (`nodes`, `edges`, `meta` tables), which the reasoner loads |

## Inspect the graph with SQL

```
sqlite3 knowledge_state/graph.db
SELECT type, COUNT(*) FROM nodes GROUP BY type;
SELECT dst, type, COUNT(*) FROM edges WHERE type IN ('RECOMMENDS', 'OPPOSES') GROUP BY dst, type;
SELECT json_extract(props, '$.snippet') FROM nodes
  WHERE type = 'Outcome' AND json_extract(props, '$.polarity') = 'bad' LIMIT 5;
```

Windows does not ship the `sqlite3` command; DB Browser for SQLite opens `graph.db` directly.

## Check the extraction rules

`eval/` holds two labeled sheets: 150 random comments (advice / outcome / both / noise) and 50 comments the rules read as outcome stories (is it really one, what the writer chose, how it went). To re-run the check with the current rules:

```
python cli.py eval              # writes eval/results.json, no raw data needed
```

Current results: advice precision 0.83 and recall 0.52; 45 of 50 outcome stories are real, with the choice right for 30 and the result right for 19. What these numbers mean is in [approach.md](approach.md#how-well-the-rules-work). To label a new sample: `python cli.py label-sample --force`, fill in the empty columns, then `python cli.py eval`.

## Tests

```
python -m unittest discover -s tests
```

38 tests cover the situation parser, the comment rules (negations, context-dependent phrases, other people's stories inside a comment, pay growth) and a full build plus queries on a few synthetic threads.

## Configuration

No environment variables, API keys or accounts are needed; Arctic Shift is public. All settings are in `careergraph/config.py`: subreddit, date range, thread limits, request pacing, the options and which ones fit each position, evidence weights, credibility weights, era weights, matching weights and the verdict thresholds. Change a value and run `python cli.py build` again.
