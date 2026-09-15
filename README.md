
# Fire/EMS Grant Command Center

A Fire/EMS-specific grant management and AI drafting application built with Streamlit.

## Main features

- Permanent SQLite department profile
- Department statistics database
- Multi-year fire/EMS call-volume history
- Equipment and inventory needs database
- NFPA / ISO / OSHA / state / protocol reference tracking
- Community demographics database
- Prior grant history
- Current grant project management
- Grant budget tables
- Custom scoring-rubric builder
- Rubric-driven AI grant writer
- Saved AI drafts
- CSV data export
- Full SQLite database backup

## AI grant writer

The AI writer uses the department database, selected grant, budget, and scoring rubric to create a complete working draft.

It is instructed to:
- address every rubric criterion;
- use entered statistics as evidence;
- connect equipment needs to operational impact;
- identify missing information as `[DATA NEEDED]`;
- avoid inventing NFPA/ISO requirements, demographics, call volume, costs, quotes, or outcomes;
- produce a final rubric-readiness review.

## Installation

Install Python 3.10 or newer.

```bash
pip install -r requirements.txt
streamlit run app.py
```

## OpenAI API

The AI writer supports the OpenAI Responses API.

You can either:
1. enter an API key in the app during the session; or
2. set an environment variable:

### Windows PowerShell
```powershell
$env:OPENAI_API_KEY="your_key_here"
streamlit run app.py
```

### macOS/Linux
```bash
export OPENAI_API_KEY="your_key_here"
streamlit run app.py
```

Do not commit API keys to GitHub.

## Persistent data

The app creates:

`fire_ems_grants.db`

in the directory where the app runs.

You can change its location with:

`GRANT_DB_PATH`

For hosted deployments, persistent storage behavior depends on the hosting provider. Use the built-in database backup feature regularly.

## Suggested workflow

1. Fill out Department Profile.
2. Enter several years of call-volume history.
3. Add department statistics.
4. Add equipment/inventory needs.
5. Enter relevant NFPA/ISO/compliance records from authoritative sources.
6. Enter community demographics with sources.
7. Record prior grants.
8. Create a current grant project.
9. Build the project budget.
10. Copy the funder's exact scoring rubric into Rubric Builder.
11. Review all data.
12. Generate the AI draft.
13. Resolve every `[DATA NEEDED]` flag.
14. Verify claims and submit only after human review.

## Important

This application is a grant-writing support tool. It does not determine legal or regulatory compliance and should not replace review of the current grant notice, NFPA standards, ISO materials, state requirements, medical protocols, procurement rules, or agency policies.
