# v2 data model and report contract

## SQLite storage

v2 stores completed analyses in `data/coach.db`, using one `sessions` table.

| Data | Purpose |
| --- | --- |
| Candidate ID | Groups a learner's sessions and Progress view. |
| Source and transcript | Records what was analysed. |
| Overall score and `scores_json` | Stores five communication metrics. |
| Summary and strengths | Stores learner-facing feedback. |
| Verdicts, new issues, open issues | Enables cross-session issue tracking. |

## Multiple users

There is no login. A user is identified solely by the free-text **Candidate ID**
entered at the top of the app. That ID is the partition key for everything:

- Every write (`save_session`) stamps the row with its `candidate_id`.
- Every read (`latest_open_issues`, `all_sessions`) filters
  `WHERE candidate_id = ?`, so one learner never sees or affects another's
  history, scores, or carried-forward issues.
- Cross-session memory is per-candidate: session *N+1* for a candidate only
  loads open issues from that same candidate's most recent session.

Practical notes:

- IDs are matched exactly and case-sensitively (`priya` ≠ `Priya`). Reusing an
  ID resumes that learner's history; a new ID starts fresh.
- One SQLite file (`data/coach.db`) holds all users. This is fine for a local,
  low-concurrency demo; it is not built for many simultaneous writers.
- The live-conversation buffer lives in Streamlit session state (per browser
  tab), so two tabs are two independent conversations even before anything is
  saved. Only analysed sessions are persisted.

To create realistic multi-user demo data, run
[`seed_demo.py`](../../v2/seed_demo.py) (see [operations](operations.md)).

## Strict analysis contract

Every accepted LLM response has exactly these top-level keys:

```json
{
  "scores": {"fluency": 0, "clarity": 0, "vocabulary": 0, "grammar": 0, "confidence": 0},
  "summary": "",
  "strengths": [],
  "prior_issue_verdicts": [],
  "new_issues": []
}
```

Scores are clamped to 0–100. The one hard requirement is that all five score
metrics are present; a response missing them is retried. Everything else is
cleaned tolerantly, because a small local model is not perfectly reliable at
strict JSON: extra fields are dropped, off-list categories snap to `general`,
and each prior-issue verdict is matched back to a stored issue (by normalized
or substring description) and kept at most once. A prior issue the model does
not judge is **not** a failure — it is simply carried forward as still-open by
`Analysis.open_issues`, so a malformed or partial response can never erase
learner history.

## Issue lifecycle

```text
new issue -> open issue -> next-session verdict
                             | improved: resolved
                             | unchanged/worse: remains open
```

If a verdict is omitted, the issue remains open defensively; a malformed model
response cannot erase learner history.

