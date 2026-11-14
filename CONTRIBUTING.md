# Contributing to GeoPulse

## Branches

Use the team branch name for the work area:

- M1: `m1-data-snowflake`
- M2: `m2-sedona-spatial`
- M3: `m3-dbt-models`
- M4: `m4-dashboard-airflow`

For focused fixes, use a short descriptive branch name based on the relevant
team prefix.

## Commits

Use a concise conventional commit prefix and imperative summary, for example:

- `feat: add spatial aggregation`
- `fix: correct UTC timestamp handling`
- `test: cover loader SQL generation`
- `docs: explain Snowflake setup`

Keep commits focused on one coherent change.

## Pull requests

1. Push your branch and open a PR against the project integration branch.
2. Describe the change, rationale, and any setup or data-contract impact.
3. Link related work and include test commands/results.
4. Request review from the affected team members and resolve feedback before
   merging.

Use the repository pull-request template when opening a PR.

## Credentials and generated data

Never commit `.env`, passwords, account identifiers intended to remain private,
or other credentials. Keep local secrets in the ignored `.env` file and use
`.env.example` only for variable names and non-secret defaults. Do not commit
generated Parquet data from `data/`.
