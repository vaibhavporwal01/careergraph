import unittest

from careergraph.classify import classify_comment, outcome_polarity
from careergraph.extract import extract_situation, is_on_theme, thread_role

CTX_PRODUCT = {"current_tier": "service", "target_tier": "product", "stage": "employed"}
CTX_FRESHER = {"current_tier": "fresher", "target_tier": "service", "stage": "fresher"}


class SituationRules(unittest.TestCase):
    def test_employed_with_product_offer(self):
        s = extract_situation("I have 2 YOE at TCS, 4.5 LPA, got a product offer of 12 LPA, 90 days notice")
        self.assertEqual((s["current_company"], s["current_tier"], s["target_tier"]), ("TCS", "service", "product"))
        self.assertEqual((s["yoe"], s["current_ctc"], s["offer_ctc"], s["notice_days"]), (2.0, 4.5, 12.0, 90))

    def test_fresher_with_service_offer(self):
        s = extract_situation("Final year student, got TCS offer at 3.36 LPA. Should I join or wait for product based companies?")
        self.assertEqual((s["stage"], s["current_tier"], s["target_company"], s["offer_ctc"]), ("fresher", "fresher", "TCS", 3.36))

    def test_monthly_salary_and_offer_from(self):
        s = extract_situation("Working at Wipro for 2 years, earning 35k per month. Offer from Amazon at 18 LPA.")
        self.assertEqual((s["current_company"], s["target_company"]), ("Wipro", "Amazon"))
        self.assertEqual((s["yoe"], s["current_ctc"], s["offer_ctc"]), (2.0, 4.2, 18.0))

    def test_cue_words_stay_inside_their_sentence(self):
        s = extract_situation("Infosys 1.5 YOE vs product company offer\nI have 1.5 yoe at Infosys, 5 LPA. Product company offering 11 LPA.")
        self.assertEqual((s["current_ctc"], s["offer_ctc"]), (5.0, 11.0))

    def test_no_offer_yet(self):
        s = extract_situation("Working at Accenture for 3 years, 7 LPA, Pune. No offer yet. Should I switch now?")
        self.assertEqual((s["has_offer"], s["current_ctc"], s["city"]), (False, 7.0, "Pune"))

    def test_switching_language_is_not_on_theme(self):
        self.assertFalse(is_on_theme("How to switch to Python?", "I work at TCS as a Java dev and want to switch to Python."))
        self.assertTrue(is_on_theme("How to switch from SBC to PBC?", "2 YOE at Infosys."))

    def test_thread_roles(self):
        self.assertEqual(thread_role("Infosys is firing employees", "Many people on bench got calls from HR."), "experience")
        self.assertEqual(thread_role("Got TCS offer, should I join?", ""), "decision")
        self.assertIsNone(thread_role("Best laptop for coding?", "Budget 60k"))

    def test_theme_filter(self):
        self.assertTrue(is_on_theme("Service based vs product based?", ""))
        self.assertTrue(is_on_theme("Need advice", "I'm at Infosys and got an offer from a startup"))
        self.assertFalse(is_on_theme("Best laptop for coding?", "Budget 60k"))


class CommentRules(unittest.TestCase):
    def test_join_and_keep_interviewing(self):
        r = classify_comment("Join TCS, don't sit idle. Keep applying while working.", CTX_FRESHER)
        self.assertTrue(r["is_advice"])
        self.assertEqual(r["stances"], {"accept_service": 1, "accept_and_keep_interviewing": 1})

    def test_against_service(self):
        r = classify_comment("Don't join TCS. Wait for a product company, the bond is a trap.", CTX_FRESHER)
        self.assertEqual(r["stances"], {"accept_service": -1, "wait_for_product": 1})
        self.assertIn("bond", r["factors"])

    def test_generic_offer_reads_thread_context(self):
        self.assertEqual(classify_comment("Take the offer. Service companies will not give you this hike.", CTX_PRODUCT)["stances"], {"switch_now": 1})
        self.assertEqual(classify_comment("Take the offer, a job in hand matters more right now.", CTX_FRESHER)["stances"], {"accept_service": 1})

    def test_outcome_upskill_then_switch(self):
        r = classify_comment("I was in the same boat. I joined TCS in 2021 and switched to a product startup after 1.5 years "
                             "of DSA prep. Best decision, got a 3x hike.", CTX_PRODUCT)
        self.assertEqual((r["kind"], r["outcome"]["chose"], r["outcome"]["polarity"]), ("outcome", "upskill_then_switch", "good"))
        self.assertEqual(r["outcome"]["situation"]["current_tier"], "service")

    def test_outcome_switch_bad(self):
        r = classify_comment("I switched to a startup right away and got laid off in 6 months. Regret it.", CTX_PRODUCT)
        self.assertEqual((r["outcome"]["chose"], r["outcome"]["polarity"]), ("switch_now", "bad"))

    def test_describing_negotiation_is_not_advice(self):
        self.assertEqual(classify_comment("With the background you have, terms will never be in your favour on the negotiation table.", CTX_PRODUCT)["stances"], {})
        self.assertEqual(classify_comment("Negotiate based on that. They usually have room.", CTX_PRODUCT)["stances"], {"negotiate": 1})

    def test_turning_down_product_offer_means_staying(self):
        r = classify_comment("I was like your friend. I rejected the Google offer back in 2013 and I regret it to this day.", CTX_PRODUCT)
        self.assertEqual((r["outcome"]["chose"], r["outcome"]["polarity"]), ("accept_service", "bad"))

    def test_reason_is_not_the_result(self):
        r = classify_comment("I left TCS within a year for a product startup because the team was really toxic.", CTX_PRODUCT)
        self.assertEqual((r["outcome"]["chose"], r["outcome"]["polarity"]), ("switch_now", "unknown"))

    def test_someone_elses_job_is_not_my_outcome(self):
        r = classify_comment("When my neighbour started working in TCS his salary was 3 lpa, and when I joined college it was still the same.", CTX_PRODUCT)
        self.assertFalse(r["is_outcome"])

    def test_switching_courses_is_not_an_outcome(self):
        self.assertFalse(classify_comment("I finished the html course and then I switched to the odin project. Now I feel lost.", CTX_PRODUCT)["is_outcome"])

    def test_quitting_to_prepare_is_its_own_option(self):
        self.assertEqual(classify_comment("Don't quit your job to prepare for another job. Study in office.", CTX_PRODUCT)["stances"],
                         {"resign_without_offer": -1})
        r = classify_comment("I quit my job to prepare for product companies. Been jobless for 8 months now, big mistake.", CTX_PRODUCT)
        self.assertEqual((r["outcome"]["chose"], r["outcome"]["polarity"]), ("resign_without_offer", "bad"))

    def test_i_did_it_reports_the_advised_option(self):
        r = classify_comment("Don't quit your job. I did it and have been jobless for almost 2 years now.", CTX_PRODUCT)
        self.assertEqual((r["outcome"]["chose"], r["outcome"]["polarity"]), ("resign_without_offer", "bad"))

    def test_pay_growth_counts_as_good(self):
        r = classify_comment("12 years ago I joined Infosys at 3 LPA. I'm sitting on 1.2 Cr right now in fintech.", CTX_FRESHER)
        self.assertEqual((r["outcome"]["chose"], r["outcome"]["polarity"]), ("accept_service", "good"))

    def test_leaving_college_is_not_a_career_move(self):
        self.assertFalse(classify_comment("I still got a role for 15 LPA when I left college. Now I'm happy with it.", CTX_PRODUCT)["is_outcome"])

    def test_later_move_means_stay_then_switch(self):
        r = classify_comment("I started at Tech Mahindra ten years ago making 3.2 LPA, and now I'm a staff engineer at a PBC making around 80 LPA.", CTX_FRESHER)
        self.assertEqual((r["outcome"]["chose"], r["outcome"]["polarity"]), ("upskill_then_switch", "good"))

    def test_leaving_needs_a_destination(self):
        self.assertFalse(classify_comment("I left TCS last year and I don't know about recent developments now.", CTX_PRODUCT)["is_outcome"])

    def test_an_offer_amount_is_not_pay_growth(self):
        self.assertEqual(outcome_polarity("I joined Capgemini at 4 LPA. After 3 years it's 4.8 LPA and I got an offer of 12 LPA now."), "unknown")

    def test_other_peoples_choices_are_not_mine(self):
        r = classify_comment("I started working at an early stage startup after graduation, and the people around me who joined WITCH "
                             "are still on bench. Best decision.", CTX_FRESHER)
        self.assertEqual((r["outcome"]["chose"], r["outcome"]["polarity"]), ("wait_for_product", "good"))

    def test_negated_bad_words(self):
        self.assertEqual(outcome_polarity("I left in 2020 after 2 years. I wasn't on bench and learned a lot."), "good")

    def test_declining_service_for_a_startup(self):
        r = classify_comment("I rejected Infosys and worked at a startup. Never regretted since.", CTX_FRESHER)
        self.assertEqual((r["outcome"]["chose"], r["outcome"]["polarity"]), ("wait_for_product", "good"))
        r = classify_comment("I quit my last job without having another offer lined up. Been jobless for 6 months now.", CTX_PRODUCT)
        self.assertEqual(r["outcome"]["chose"], "resign_without_offer")

    def test_polarity_negations(self):
        self.assertEqual(outcome_polarity("No regrets at all, best move."), "good")
        self.assertEqual(outcome_polarity("Not happy, it was a mistake."), "bad")
        self.assertEqual(outcome_polarity("Pay is much better but I regret the toxic culture."), "mixed")

    def test_reply_hint_and_noise(self):
        self.assertEqual(classify_comment("Disagree. Startups are risky right now, stay at TCS.", CTX_PRODUCT)["reply_hint"], "DISAGREES")
        self.assertEqual(classify_comment("following", CTX_PRODUCT)["kind"], "noise")


if __name__ == "__main__":
    unittest.main()
