# Contributing

Thank you for helping improve the job screening engine.

## Privacy boundary

Use synthetic examples and fixtures only. Do not commit real job-search data,
including applicant details, recruiter or referral information, application
records, private compensation criteria, or non-public job postings.

Do not commit secrets, tokens, credentials, environment files, generated
reports, or local caches. Report suspected vulnerabilities through the
repository's private vulnerability reporting form instead of a public issue.

## Pull requests

1. Create a focused branch and open a pull request against `main`.
2. Run `python -m unittest discover -s tests -v` locally.
3. Keep GitHub Actions references pinned to full commit SHAs.
4. Confirm that the Python 3.11, Python 3.14, and CodeQL checks pass.
5. Resolve every review conversation before merge.

The repository uses linear history, signed commits on `main`, and squash
merging. Feature branches are retained unless their owner intentionally
removes them.
