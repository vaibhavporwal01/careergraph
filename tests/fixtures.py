"""Synthetic threads for tests only. Not real Reddit data; users and text are made up."""

T0 = 1717200000  # 2024-06-01


def _thread(pid, title, body, comments):
    post = {"id": pid, "title": title, "selftext": body, "author": f"op_{pid}", "created_utc": T0, "score": 10, "num_comments": len(comments)}
    items = [{"id": cid, "author": author, "body": text, "parent_id": f"t1_{parent}" if parent else f"t3_{pid}",
              "link_id": f"t3_{pid}", "score": score, "created_utc": T0 + 60 * (i + 1)}
             for i, (cid, author, parent, score, text) in enumerate(comments)]
    return post, items


THREADS = [
    _thread("t1", "2 YOE at TCS, got product offer 12 LPA, should I switch?",
            "Currently working at TCS with 2 years of experience, ctc 4.5 LPA. Got an offer from a product startup for 12 LPA. "
            "Notice period is 90 days. Confused.", [
                ("c11", "user_a", None, 40, "Switch now. You will learn much more and the pay jump is huge."),
                ("c12", "user_b", None, 55, "I was in the same spot. I left TCS after 2 years and joined Flipkart. Best decision, got a 2x hike."),
                ("c13", "user_c", "c11", 12, "Disagree. Startups are risky right now, layoffs everywhere. Stay at TCS, prepare for a year, then switch."),
                ("c14", "user_d", None, 5, "Negotiate with the startup for 14, they usually have room."),
            ]),
    _thread("t2", "Infosys 1.5 YOE vs product company offer",
            "I have 1.5 yoe at Infosys, 5 LPA. Product company offering 11 LPA. 60 days notice.", [
                ("c21", "user_a", None, 30, "Take the offer. Service companies will not give you this hike."),
                ("c22", "user_e", None, 25, "I switched from Wipro to a startup in 2023 and got laid off in 6 months. Regret it. Check their funding first."),
                ("c23", "user_f", None, 8, "Go for it. I'd recommend switching now while you are early in your career."),
                ("c24", "user_b", None, 20, "Same story here, I moved to a product company after 1 year and I am much happier now, learned a lot."),
            ]),
    _thread("t3", "Final year, got TCS offer. Join or wait for product?",
            "Fresher here, campus placement in TCS 3.6 LPA. Should I join or wait for product based companies?", [
                ("c31", "user_c", None, 15, "Join TCS, don't sit idle. Keep applying while working."),
                ("c32", "user_g", None, 22, "Don't join TCS. Wait for a product company, the bond is a trap."),
                ("c33", "user_a", None, 18, "I joined TCS as a fresher and was on bench for 8 months. Worst decision. Now at a startup after preparing DSA."),
            ]),
    _thread("t4", "3 YOE Accenture, should I move to product?",
            "Working at Accenture for 3 years, 7 LPA, Pune. Want to switch to product based. 90 days notice is a problem.", [
                ("c41", "user_h", None, 14, "Upskill in system design for 3 months then switch. Notice period will be the biggest blocker, start applying early."),
                ("c42", "user_b", None, 9, "I resigned without an offer to skip the 90 day notice and it took me 7 months to land a job. Mistake."),
            ]),
    _thread("t5", "TCS 2 YOE, offer from Amazon 18 LPA",
            "2 yoe at TCS, ctc 4 LPA, offer from Amazon at 18 LPA, 90 days notice. Is it worth it?", [
                ("c51", "user_f", None, 33, "Accept it, Amazon is a great brand on your resume."),
                ("c52", "user_e", None, 6, "Negotiate for an early release from TCS, they often agree."),
            ]),
    _thread("t6", "Infosys is firing employees", "Heard many people got calls from HR this week.", [
                ("c61", "user_i", None, 21, "I stayed and now I am on bench for 6 months. Worst decision."),
                ("c62", "user_j", None, 11, "Glad I left Infosys last year for a startup, best decision of my life."),
            ]),
]
