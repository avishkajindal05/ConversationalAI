# ─── v2/seed_demo.py ───
"""Seed the coach database with demo users, conversations, and reports.

Creates a few candidates with several sessions each and runs the *real*
analysis pipeline (Ollama + the strict schema + cross-session issue
carry-forward), so the Progress view has genuine trends to show. Each persona
is written to illustrate a different trajectory:

  * priya_demo  — nervous starter who steadily improves session over session
  * rahul_demo  — a rambler whose clarity issue is stubborn, then eases
  * sara_demo   — an already-strong communicator who stays consistently high

Run it (Ollama must be up with the model pulled):

    python -m english_coach.v2.seed_demo          # add demo data
    python -m english_coach.v2.seed_demo --reset  # wipe demo users first

Only the demo candidate IDs are ever touched; real learner rows are left alone.
"""

from __future__ import annotations

import argparse
import sqlite3

from english_coach.v2.coach import db
from english_coach.v2.coach.analysis import analyze
from english_coach.v2.coach.conversation import transcript_text

# Each session is a list of (speaker, text) turns. "user" turns are what gets
# scored; "coach" turns are context, mirroring a real conversation.
Conversation = list[tuple[str, str]]

DEMO: dict[str, list[Conversation]] = {
    "priya_demo": [
        # Session 1 — nervous, lots of fillers, thin answers.
        [
            ("coach", "Hi Priya! What have you been up to lately?"),
            ("user", "um yeah so like i been, you know, just working and stuff, "
                     "it's been kinda busy i guess, i dunno."),
            ("coach", "Sounds busy! Anything at work you enjoyed?"),
            ("user", "um not really, like there was a meeting thing, it was okay i "
                     "think, i didn't really say much to be honest."),
            ("coach", "That's alright. What would you like to feel more confident about?"),
            ("user", "um speaking up maybe, like in front of people, i get nervous and "
                     "then i just, you know, freeze up a bit."),
        ],
        # Session 2 — still some fillers, but more structure and detail.
        [
            ("coach", "Good to see you again, Priya. How did the week go?"),
            ("user", "It went pretty well actually. I had to present our project update, "
                     "and I prepared a few notes beforehand so I felt a bit calmer."),
            ("coach", "That's great preparation. How did the presentation land?"),
            ("user", "Um, I think it went okay. I still said 'like' a lot, but people "
                     "understood the main points and asked a couple of questions."),
            ("coach", "Nice progress. What is your goal for next time?"),
            ("user", "I want to slow down and cut the filler words, and maybe make eye "
                     "contact instead of looking at my notes the whole time."),
        ],
        # Session 3 — confident, structured, minimal fillers.
        [
            ("coach", "Welcome back, Priya. Tell me about a recent win."),
            ("user", "This week I led the team stand-up for the first time. I opened "
                     "with the goal, gave each person space to update, and closed with "
                     "clear next steps and owners."),
            ("coach", "That's a big step up. How did it feel?"),
            ("user", "Honestly, much more in control. I spoke slowly, kept my points "
                     "short, and I noticed I barely used any filler words this time."),
            ("coach", "Wonderful. What are you focusing on now?"),
            ("user", "Now I want to work on asking better follow-up questions so the "
                     "conversation feels two-way rather than just me reporting."),
        ],
    ],
    "rahul_demo": [
        # Session 1 — rambling, hard to follow, buries the point.
        [
            ("coach", "Hi Rahul! What's something interesting from your week?"),
            ("user", "So basically there was this whole situation with the project and "
                     "the client and also the deadline moved but then it moved back and "
                     "there were emails going around and I was in three meetings and one "
                     "of them wasn't really needed and anyway eventually we sort of "
                     "figured it out but it took forever and it was a whole thing."),
            ("coach", "That is a lot going on! What was the key outcome?"),
            ("user", "Well the outcome was kind of that we delivered it but also there "
                     "were bits that weren't done and we said we'd do them later and I'm "
                     "not totally sure who owns that part to be honest, it got confusing."),
        ],
        # Session 2 — still rambling; clarity issue persists.
        [
            ("coach", "Welcome back, Rahul. How did the launch go?"),
            ("user", "The launch, right, so we launched but there were a few things, like "
                     "the config wasn't set and then someone changed it and then it broke "
                     "and we rolled back and then rolled forward and there were a lot of "
                     "messages and it was busy and eventually it was fine I think."),
            ("coach", "Glad it's stable now. If you summarised it in one sentence?"),
            ("user", "One sentence is hard because there were so many parts, but I guess "
                     "we launched, it broke a bit, and then we fixed it, roughly."),
        ],
        # Session 3 — noticeably tighter; starting to lead with the point.
        [
            ("coach", "Hi Rahul. Give me the headline from this week."),
            ("user", "We shipped the reporting feature on time. There was one config "
                     "issue at launch, I rolled it back, fixed the setting, and re-deployed "
                     "within an hour."),
            ("coach", "That's a clear summary. What made the difference?"),
            ("user", "I tried to state the outcome first and then the details, instead of "
                     "telling the whole story in order. It's still a work in progress but "
                     "people followed it much more easily."),
        ],
    ],
    "sara_demo": [
        # Session 1 — already strong: structured, specific, confident.
        [
            ("coach", "Hi Sara! What's a recent project you're proud of?"),
            ("user", "I redesigned our onboarding flow. I started by interviewing five "
                     "new users, mapped where they dropped off, and cut the steps from "
                     "nine down to four. Activation went up by about twenty percent."),
            ("coach", "Impressive and measurable. What was the hardest part?"),
            ("user", "Getting alignment. Two teams owned different steps, so I ran a short "
                     "workshop, showed the drop-off data, and we agreed on a single owner "
                     "for the whole flow. The data made the decision easy."),
        ],
        # Session 2 — consistently clear and confident.
        [
            ("coach", "Good to see you, Sara. What's on your plate now?"),
            ("user", "I'm mentoring two junior designers. Each week we pick one real task, "
                     "I let them lead, and I give feedback afterwards focused on one thing "
                     "at a time so it doesn't overwhelm them."),
            ("coach", "That's a thoughtful approach. How's it working?"),
            ("user", "Really well. One of them just shipped her first feature solo, and she "
                     "told me the one-thing-at-a-time feedback made it feel manageable."),
        ],
    ],
}


def _demo_ids() -> list[str]:
    return list(DEMO.keys())


def reset() -> None:
    """Remove only the demo candidates so the script is safe to re-run."""
    db.init_db()
    with sqlite3.connect(db.DB_PATH) as conn:
        conn.executemany(
            "DELETE FROM sessions WHERE candidate_id = ?",
            [(cid,) for cid in _demo_ids()],
        )
    print(f"Cleared demo users: {', '.join(_demo_ids())}")


def _to_messages(conversation: Conversation) -> list[dict]:
    return [{"role": role, "content": text} for role, text in conversation]


def seed() -> None:
    db.init_db()
    for candidate_id, sessions in DEMO.items():
        print(f"\n=== {candidate_id} ===")
        for i, conversation in enumerate(sessions, 1):
            transcript = transcript_text(_to_messages(conversation))
            prior = db.latest_open_issues(candidate_id)
            result = analyze(transcript, prior)
            open_issues = result.open_issues(prior)
            db.save_session(candidate_id, "live", transcript, result, open_issues)
            verdicts = ", ".join(
                f"{v.description[:24]}…={v.status}" for v in result.prior_issue_verdicts
            )
            print(
                f"  session {i}: overall={result.overall_score:>5}"
                f"  new_issues={len(result.new_issues)}"
                f"  open_now={len(open_issues)}"
                + (f"  verdicts[{verdicts}]" if verdicts else "")
            )
    print("\nDone. Open the app and enter one of these Candidate IDs:")
    print("  " + "  ".join(_demo_ids()))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reset", action="store_true", help="wipe demo users before seeding"
    )
    args = parser.parse_args()
    if args.reset:
        reset()
    seed()


if __name__ == "__main__":
    main()
