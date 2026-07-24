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

Scores are clamped to 0–100. Each prior issue must appear exactly once with an
`improved`, `unchanged`, or `worse` verdict. Extra fields, missing metrics,
duplicate verdicts, and missing prior-issue verdicts cause a retry.

## Issue lifecycle

```text
new issue -> open issue -> next-session verdict
                             | improved: resolved
                             | unchanged/worse: remains open
```

If a verdict is omitted, the issue remains open defensively; a malformed model
response cannot erase learner history.

