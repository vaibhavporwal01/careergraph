# Approach

## The problem I picked

Almost every week r/developersIndia gets a version of the same post: "I'm at TCS / Infosys with 1 to 3 years, I have a product company offer, what should I do?" or "Final year, got a service company offer, should I join or wait for product?" The answers already exist, spread across hundreds of threads. Searching them does not help much, for three reasons:

- **Advice only makes sense for a situation.** "Switch now" from someone with 6 YOE in Bangalore means little to a fresher with a training bond. Search cannot filter by situation.
- **Upvotes reward confidence, not experience.** The top comment is often the most confident one, not the one from someone who was actually in that spot.
- **The most useful replies are buried.** "I did X, here is what happened" comments are rare, and they look the same as every other comment.

So I picked one decision, service vs product, and built a graph that separates situations, options, advice, outcomes, factors and authors. When someone describes their situation, the system works out where they stand, finds similar situations through the graph, weighs advice and real outcomes by who said them and when, and returns something they can act on: the decision that fits best with a confidence level, tips that go with it, the main dissenting view, what happened to people in similar spots, risk flags, and whose opinion to trust.

## Data subset and why

- **Source:** r/developersIndia through the Arctic Shift archive, posts from 2021-01-01 up to the fetch date.
- **Theme:** service vs product decisions. That covers freshers with a service offer deciding whether to join or hold out, and engineers in service companies deciding whether, when and how to switch.
- **Why this theme:** situations here have hard attributes that rules can pull out (company, YOE, CTC, notice period). People do report what happened after they chose. And opinions genuinely split, so "consensus vs dissent" means something. A topic like "best laptop for coding" fails all three.
- **Why from 2021:** it covers the 2021-22 hiring boom and the slowdown after it, so advice from different market conditions can be treated differently.

How threads get picked (`careergraph/fetch.py`):

1. Page through the subreddit's post listing one day at a time and keep only posts whose title passes a loose topic pre-filter (company names, "offer", "switch", "fresher" and similar) and that have at least 5 comments. The archive's title search timed out in testing, even on one-month windows, while listing a single day worked reliably. So the listing works as the search: each title is checked as it comes in, and titles that don't match are dropped on the spot. Nothing outside the pre-filter is stored.
2. Fetch the bodies of the kept posts and sort them with a hand-written rule:
   - A **decision thread** names a service company (by name, or as "service based", "WITCH", "SBC") and its title has a job-move word (offer, join, quit, switch to a company, which one, vs) or says "service vs product". A vague title like "need advice" only counts if one body sentence has both. "Switch to Python" or "switch to Dev" is not a job move.
   - An **experience thread** has a service company in the title but no decision, like "Infosys is firing employees". People share what happened to them there, so I keep these for outcome stories only. Their advice is not about anyone's specific situation, so it is left out.
3. Download all comments for the 1,000 most discussed decision threads and 250 experience threads. The build keeps threads with at least 10 usable comments: up to 800 decision and 200 experience threads. Below 10 comments a thread rarely has disagreement or an outcome report.

Left out: bot comments (AutoModerator, devsIndiaBot), removed or deleted text, the original poster's own replies, and the same person posting the same comment twice.

What the snapshot in this repo holds:

| Step | Count |
|---|---|
| Days covered | 2,119 (1 Jan 2021 to 20 Oct 2026) |
| Titles checked against the topic filter | 351,054 (not stored) |
| Titles kept, post texts fetched | 27,693 |
| Threads found | 3,797 decision, 1,213 experience |
| Threads downloaded with comments | 1,250 (1,000 decision, 250 experience) |
| Threads in the graph | 1,000 (800 decision, 200 experience), from 2021-02-19 to 2026-10-19 |
| Comments read | 67,378: 12,309 advice, 267 outcome stories, 54,802 noise |
| Authors | 7,649 |

So the project keeps about 8% of the subreddit's titles from that period, downloads full comments for 0.4% of its threads, and builds the graph from 1,000 threads.

Threads per year in the graph: 2021: 21, 2022: 90, 2023: 141, 2024: 239, 2025: 307, 2026: 202. The subreddit grew a lot, so recent years dominate, which suits the era weights below. Everything else is in `knowledge_state/summary.json`.

## Entities

| Node | What it is | Why it is its own node |
|---|---|---|
| Question | Opening post of a thread, marked as a decision or experience thread | Anchors every piece of advice to the situation it was written for |
| Situation | Current company and tier, target company and tier, YOE, current CTC, offer CTC, notice period, city, stage | The same shape describes a question, the writer of an outcome, and an author's own job. New input is matched situation to situation, so it had to be a node, not columns on a post |
| Option | One of 7 fixed options: 5 decisions and 2 tactics | Free-text advice cannot be added up. A closed set lets me total support and pushback per option |
| Advice | A comment telling someone what to do | Opinion, weighted as opinion |
| Outcome | A comment where the writer says what they chose and how it went (good / bad / mixed / unknown) | Evidence, not opinion. Kept apart so it can be weighted differently |
| Factor | Pay, learning, job security, work-life balance, notice period, bond, bench time, brand value | Lets me compare what people warn about with what actually went wrong |
| Author | A Reddit user with a credibility score | Lets the same comment count more or less depending on who wrote it |

The options:

| Option | Kind |
|---|---|
| Join or stay in the service company | decision |
| Hold out for a product company | decision |
| Take the product / startup move now | decision |
| Stay for now, prepare, switch later | decision |
| Quit first, then search | decision |
| Negotiate before you decide | tactic |
| Keep interviewing after you join | tactic |

The answer picks one decision. Tactics go with any decision, so they are shown as tips next to it. I started with six options ranked together and no "quit first". The full run showed why that did not work (see "What the full run changed").

## Relationships

| Edge | Between | What it captures |
|---|---|---|
| HAS_SITUATION | Question -> Situation | The asker's parsed situation |
| ASKED, GAVE, REPORTED | Author -> Question / Advice / Outcome | Who said what |
| ANSWERS | Advice -> Question | Which situation the advice was given for |
| RECOMMENDS, OPPOSES | Advice -> Option | Stance, with negation handled ("don't join TCS" opposes) |
| CITES | Advice -> Factor | What the advice is based on |
| SUPPORTS, DISAGREES | Advice -> Advice | Direct replies that back or push back on their parent |
| CHOSE | Outcome -> Option | What the person did, with polarity on the edge |
| FROM | Outcome -> Situation | The situation the person was in when they chose |
| MENTIONS | Outcome -> Factor | What the outcome was about |
| IN_THREAD | Outcome -> Question | Where it was said |
| WAS_IN | Author -> Situation | What the author said about their own job in these threads |

Decisions in the model worth calling out:

1. **Context changes meaning.** "Take the offer" maps to joining the service company in a fresher thread with a TCS offer, and to taking the product move in a thread where a service engineer has a product offer. The mapping reads the thread's Situation node instead of guessing from the comment alone.
2. **One comment, one vote per option.** If a comment is both an outcome and advice for the same option ("I switched, best decision, you should too"), only the outcome counts.
3. **Outcomes keep their own situation when they state one** ("I was at Infosys with 2 YOE..."). When they don't, they borrow the thread's situation at 0.7 weight, since commenters often write "I was in the same spot" without details. In experience threads they only borrow "works at a service company", because people commenting there were not in the asker's spot.
4. **Credibility is not karma.** 0.4 lived experience (the author described their own job in these threads), 0.3 outcome reports (one report gives half, two or more give full), 0.2 upvote percentile within the thread (shrunk toward the middle for people with one or two comments, so one lucky comment does not decide it), 0.1 network rank. The network part is PageRank over who answered whom, an idea from Zhang, Ackerman and Adamic's study of expertise in the Java Forum. The PageRank is hand-written, with no graph library; it is a few lines. Credibility scales each piece of evidence between 0.5x and 1x, so it changes how much a comment counts without overriding the outcome vs advice weight.
5. **Market eras.** Before July 2022 counts as the boom (weight 0.6), July 2022 to 2023 as the slowdown (0.8), 2024 onward as current (1.0). "Just switch" advice from 2021 was given in a different hiring market.
6. **Where the asker stands decides which decisions fit.** A fresher has no job to quit, and someone holding a product offer has nothing to hold out for:

   | Position | Decisions that fit |
   |---|---|
   | Fresher | join the service company, hold out for product, take a product or startup offer |
   | Holding a product or startup offer | take it, stay, stay and switch later |
   | Employed, no product offer | stay, switch now, stay and switch later, quit first |

7. **Stories are read from the asker's position.** "Joined TCS, prepared, switched after 2 years" is where a fresher's "join the service company" leads, so for a fresher it counts toward joining. For someone holding a product offer it is the jump they are about to make, so it counts toward taking it.

## How the knowledge representation is built

Everything is hand-written rules, with no extraction library, split across three files:

- `lexicon.py`: a company dictionary (26 service and 42 product companies with their aliases, like "infy" or "tata consultancy"), generic tier phrases ("service based", "WITCH", "product company", "startup"), city names, and all the phrase rules for advice, outcomes, options, factors and replies.
- `extract.py`: turns text into a Situation. Money is normalized to LPA from forms like "12 LPA", "12L", "35k per month", "1.2 cr" and "Rs 6,00,000". YOE comes from "2 YOE", "2 years of experience", "working at X for 2 years" or "18 months". Fresher words set YOE to 0. Whether a company or amount is the current side or the offer side is decided by the nearest cue word in the same sentence ("working at", "left", "from" vs "offer from", "switch to", "selected in"). When two amounts appear with no cue words ("4.5 to 12"), the smaller is current and the larger is the offer.
- `classify.py`: labels each comment.
  - **Advice** needs a sentence phrased as advice (an imperative, "you should", "better to") or a general advice marker. Stances only come from sentences phrased as advice.
  - **Outcome** needs a first-person decision verb ("I joined", "I switched", "I declined") plus a result marker ("best decision", "laid off", "2 years later"). A comment like "Don't quit your job. I did it and have been jobless for 2 years" counts as an outcome for the option it advises about.
  - **What the person chose** is decided by ordered rules. Quitting with nothing lined up is checked first. Leaving a job only counts as the product move when the story says where they went. Joining a service company and later moving to product counts as "stay, then switch", and how it went is judged from the move onward.
  - **How it went** handles negations both ways ("no regrets" is positive, "wasn't on bench" is not negative). It ignores the reason for a decision ("because the team was toxic"), what other people said ("my team said I was making a mistake") and other people's part of a sentence ("the people around me who joined WITCH are on bench"). Pay growing to 1.5x or more counts as good, but only when the later amount is what the writer earns, not an offer or someone else's salary.
  - **Disagreement** is checked only on direct replies between two advice comments: explicit words ("disagree", "bad advice") or stances that conflict.

The graph is saved as plain nodes and edges tables in SQLite with JSON properties, plus a JSON export with one item per line. I chose that over a graph database because anyone can open it without a server, and at about 21,000 nodes the reasoner loads everything into memory and answers in about a second.

Tradeoffs made on purpose:

- **Precision over recall.** Rules miss sarcasm, Hinglish ("join kar lo") and advice with no cue words. A smaller graph that can be trusted is worth more than a bigger noisy one.
- **No sentiment library.** Outcome polarity comes from hand-written phrase lists, so every label can be traced to the phrase that caused it.
- **The rules are measured, not assumed to work.** The numbers and what they mean are in "How well the rules work" below.

### What the first real run changed

The first run used three months of data (January to March 2024). Of 17 comments the rules marked as outcome stories, only 2 were right, and the example question came back with "high confidence" for an option nobody had reported trying. The fixes that came from reading those results:

- **How it went is read from the "I did X" sentence onward**, without the reason ("because the team was toxic") and without lines addressed to the reader. Before this, rant words anywhere in the comment decided whether an outcome was good or bad.
- **"Switched" only counts when the object is a job or a company.** "I switched to the Odin Project" was being read as a career move.
- **Turning down a product offer means staying put.** "I rejected the Google offer and regret it" is a bad outcome for staying, not for holding out.
- **Option cues only count in sentences phrased as advice.** "Your negotiation skills are weak" was being counted as a recommendation to negotiate.
- **The topic filter needed real job-move words.** "How to switch to Python?" got in because of the word "switch".
- **Confidence uses outcome reports for the recommended option only.** Before, it counted outcomes for every option.
- **Experience threads exist because of this run.** The stricter filter removed threads like "Infosys is firing employees", which held the only real bench stories.

After these changes the same three months gave 13 outcome stories, read correctly or marked "unknown" when the comment did not say how it went.

### What the full run changed

Testing the full graph on seven situations gave answers that did not make sense for anyone already holding an offer. Samples of the outcome stories showed why:

1. **Tactics won by default.** Nobody argues against negotiating or keeping interviews going, and nobody reports how it went, so these two came out on top whenever the real decisions were debated. A 5 YOE Infosys engineer with a 30 LPA Amazon offer was told to negotiate, although 30 advice comments said take it and 3 said don't. They are tips now.
2. **Quitting with nothing lined up was mixed into taking an offer.** Advice like "don't quit your job to prepare" and stories like "I resigned without an offer, jobless for 8 months" were counted against taking a product offer. "Quit first, then search" is its own decision now. Across the graph, 170 advice comments argue against it and 32 for it.
3. **One outcome counted like about 16 advice comments, not 3.** People who report outcomes are by design the most credible authors (median credibility 0.65, against 0.12 for advice writers), so the 3x weight got applied twice. Scaling evidence between 0.5x and 1x brings it to about 4 to 1 at the medians.
4. **Decisions were recommended where they don't fit.** The same Amazon case got "hold out for a product company" at one point. The position table above fixes that.
5. **Story reading.** People who joined a service company and later moved to product were counted as "stayed in service, went well", which pushed "stay" on people holding offers. Leaving a job counted as the product move even with no destination ("I left TCS last year..."). Other people's choices inside a sentence were read as the writer's, "I wasn't on bench" counted as bad, and a few comments were posted twice. Each fix has a test.

Outcome stories went from 379 to 267: fewer, but stricter. 131 of them have a clear good, bad or mixed result. The seven test situations now give sensible answers. A fresher with an Infosys offer gets "join" (128 advice comments for, 21 against), people holding a product offer get "take it", and an employed person thinking of quitting to prepare gets "stay for now, prepare, switch later", with "quit first" strongly against (38 advice comments against, 7 for).

## How well the rules work

Two labeled sheets in `eval/` check the rules:

- `labels.csv`: 150 random comments from the downloaded threads, each labeled advice, outcome, both or noise.
- `outcome_audit.csv`: 50 random comments the rules read as outcome stories, each checked for three things: is it really a story, what the writer chose, and how it went.

`python cli.py eval` runs the current rules on the same comments (their text and thread context are saved in `eval/context.json`) and writes `eval/results.json`, so the numbers always describe the rules as they are now.

Label definitions:

- **Advice**: the comment tells someone what to do or what to avoid, including recommendations ("I'd go with TCS") and one-word answers to "which one?". Opinions about a company without a recommendation are not advice.
- **Outcome**: the writer says what they decided about their own job or career and how it went or where it led. Stories about friends don't count, and neither does a decision with no result ("As soon as they made 10 hour days mandatory, I switched").
- **What they chose** follows the options: joined or stayed in a service company, held out (a fresher who skipped service for product or a startup), took the product move, stayed a while and then left the service company, or quit with nothing lined up.
- **How it went**: good, bad, mixed, or unknown when the comment doesn't say.

Results:

| Check | Result |
|---|---|
| Advice in 150 random comments (46 have advice) | precision 0.83 (24 of 29 flagged), recall 0.52 (24 of 46) |
| Stories in the same 150 (5 have one) | 1 of 5 found, no false ones; too few to say much |
| Stories the rules found: really a story | 45 of 50 (90%) |
| ...what the writer chose | right for 30 of 45 (67%) |
| ...how it went | right for 19 of 45 (42%) |

What this means:

- **The rules are careful rather than thorough.** When they call something advice or a story, they are usually right. But they miss about half the advice: short replies ("Use phone", "Always a startup", "Capgemini."), imperatives after a comma or a "bro", and Hinglish.
- **The choice goes wrong in a few repeatable ways.** A fresher who joined a startup is read as "took the product move" when the thread itself is not about freshers (5 of the 15 misses). Joining a service company and leaving years later is read as "stayed" or "switched now" (6). Waiting months for a service company's onboarding, and "waited 6 hours for an interview", are read as holding out (2).
- **How it went is the weakest part.** Of the 26 misses, 19 are "unknown" where a reader sees a clear result ("regretting it every single day", "set me up for life", "had 6 offers"), 4 are "mixed" where the story leans one way, and 3 get the direction wrong. Those 3 are long stories that describe a bad old job after the decision sentence. Unknown results carry no weight in the answer, so most misses mean fewer stories counted, not wrong ones counted.

Two hundred comments checked by one labeler is a small check, but it shows where to work next. The labels are in the two CSVs, so anyone can review or change them and re-run `python cli.py eval`.

## What happens when a new input arrives

1. **Parse** it with the same extractor into a Situation. Missing fields are reported back to the user.
2. **Work out the position:** fresher, holding a product or startup offer, or employed without one. This decides which decisions fit.
3. **Match** it against the Situation of every decision thread and of every outcome, including outcomes from experience threads. Similarity = 0.5 tier + 0.3 YOE + 0.2 CTC.
   - Tier compares the current side (0.6) and the target side (0.4). Product vs startup counts 0.6, fresher vs service 0.3.
   - YOE drops linearly to zero at 3 years apart. CTC is compared on a log scale and drops to zero at a 2.5x gap.
   - Missing fields lower the score: it is multiplied by 0.4 + 0.6 x the share of match weight both sides have.
   - Matches at 0.35 or above are kept: the top 30 threads and up to 60 outcomes.
4. **Weigh** every piece of evidence: type weight (outcome 3, advice 1) x credibility factor (0.5 to 1) x era weight x similarity. Advice adds to the support or pushback of the option it recommends or opposes. A good outcome adds support for what the person chose (read from the asker's position), a bad one adds pushback, a mixed one adds half to each.
5. **Decide** among the decisions that fit. The one with the highest net support wins. Confidence is low with fewer than 5 similar situations or fewer than 2 outcome reports for the recommended decision, high with 15+ situations, 5+ outcome reports for it and at least half of all positive net support, and medium otherwise. If nobody reported how the recommended decision turned out, the output says so plainly.
6. **Add tips.** A tactic is shown when at least 2 matched advice comments suggest it and it has more support than pushback.
7. **Show dissent.** If a rival decision has at least 40% of the winner's support, or the winner's pushback is at least 40% of its support, the output shows it with the strongest comment behind it and how many direct replies disagreed.
8. **Flag risks.** A factor becomes a risk flag when it shows up in at least 30% of bad outcomes but in under 10% of advice. These are the things people learn the hard way. If fewer than 3 bad outcomes match, this check runs on the whole graph instead.
9. **Show who to trust:** the authors behind this answer, ranked by credibility, with what they lean toward.

The verdict prints in the terminal and is saved as JSON in `outputs/`. Every number above is in `careergraph/config.py`.

## What I chose not to build

- **No embeddings or text similarity for matching.** Matching through attributes is explainable ("same tier, one year apart, similar CTC") and keeps this from turning into a search engine over Reddit.
- **No LLM anywhere.** Extraction, reasoning and output are rules and arithmetic.
- **No crawling of user histories** for credibility. Only what people said in these threads counts.
- **No use of the original poster's follow-up updates as outcomes.** They are rare and hard to tell apart from thank-you replies.
- **No web UI.** The CLI shows the reasoning step by step, which matters more here.
- **One subreddit, one decision.** Going deeper on one decision seemed more useful than going shallow on many.

## What I would build next

1. **Fix the misses the eval found, then measure again on a fresh sample.** Short replies like "Use phone" or "Always a startup", fresher stories in threads that are not about freshers, and result words like "regretting", "set me up for life" or "had 6 offers". A fresh sample matters: tuning the rules on the same 200 comments would flatter the numbers.
2. **Read two-phase stories as two linked outcomes.** "Joined TCS, bench for a year, now at a startup" is one outcome for joining and one for switching. Right now it is a single "stay, then switch".
3. Add Hinglish phrase lists, since a good share of this subreddit mixes Hindi and English.
4. Company profile nodes built from outcomes, for example which companies keep showing up with bench time or notice period trouble.
5. Calibrate the weights (3:1 for outcomes, 40/30/20/10 for credibility, the era weights) by checking which settings best predict held-out outcome polarity, instead of setting them by judgment.
6. Follow the same author across threads to get outcomes with real dates.
7. Add neighbouring decisions (MS vs job, startup vs MNC) as new options on the same graph.
