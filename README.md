# Job Screening Engine

A small, dependency-free Python engine for validating configurable job criteria,
screening local job records against hard filters, and producing transparent fit
scores.

The project is intentionally local-first. It does not scrape job boards, call
external services, submit applications, or store personal profiles. The included
configuration and candidate record are fictional examples.

## Features

- strict validation for criteria and candidate schemas;
- deterministic, explainable hard-filter decisions;
- duplicate detection across job URLs and normalized job identities;
- evidence-backed fit scoring with visible component weights;
- batch ranking that never lets a score override a hard-filter rejection;
- no runtime dependencies beyond Python's standard library.

## Quick start

Validate the example criteria:

```bash
python3 -m src validate
```

Screen or score the fictional example job:

```bash
python3 -m src screen examples/sample-job.json
python3 -m src score examples/sample-job.json
```

Screen or rank several local records:

```bash
python3 -m src screen-batch path/to/job-one.json path/to/job-two.json
python3 -m src rank-batch path/to/job-one.json path/to/job-two.json
```

Run the tests:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

CI runs the test suite on Python 3.11 and Python 3.14 using the Ubuntu 24.04
runner image. Workflow dependencies are pinned to immutable commit SHAs,
repository permissions are read-only, and checkout credentials are not
persisted. A separate repository-hygiene check rejects tracked local-data
directories, environment files, credentials, logs, spreadsheets, and database
files.

## Configuration

`config/criteria.yaml` is JSON-compatible YAML. It defines:

- accepted role families and location categories;
- a non-negative minimum guaranteed base salary;
- optional exclusion of commission-only or active-license roles;
- excluded title terms and role categories.

Each candidate record contains only the facts required for screening and
scoring. Fit ratings must include supporting evidence, and a posting must be
explicitly marked as verified before it can pass. The engine validates supplied
data; it does not independently visit or verify a source URL.

## Scoring

Accepted candidates receive a deterministic weighted score:

- required-skills coverage: 40%;
- seniority fit: 20%;
- compensation: 20%;
- location and culture fit: 20%.

Ratings are `strong`, `acceptable`, `weak`, or `unknown`. Unknown ratings receive
no assumed credit. Rejected records remain unscored.

## Privacy

Do not commit real résumés, application records, recruiter details, credentials,
or other personal data. Keep operational job-search data outside the repository
and pass local record paths to the CLI when needed.

## License and security

The project is available under the MIT License. Report vulnerabilities through
GitHub's private security-advisory workflow as described in `.github/SECURITY.md`.
