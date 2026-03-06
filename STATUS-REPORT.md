# PushToBicep Architect — Status Report

**Date:** March 6, 2026
**Sprint:** Feb 27 – Mar 6 (2 weeks)
**Author:** Jennifer Kelleman

---

## TL;DR

The PushToBicep Architect hackathon agent is **code-complete and test-passing**. Over the past two weeks, the project went from a raw scaffold to a hardened, well-documented GitLab Duo agent that converts AWS Terraform + Dockerfiles to Azure Bicep via a single `git push`. Ten reliability improvements were made to the scripts and CI pipeline. A realistic multi-tier AWS test config was added. Both test suites (33 unit tests + 3-stage e2e simulation) pass at 100%. The only remaining gate is **live API testing**, which is blocked on GitLab for Education approval (applied Mar 1, pending). The `tests/` directory is written but not yet committed — everything else is pushed to GitHub.

---

## What Was Done

### 1. Reliability Hardening (10 improvements)

| # | Improvement | Files Touched |
|---|---|---|
| 1 | Environment variable validation (fail-fast with clear error) | `invoke_duo_agent.py`, `open_migration_mr.py` |
| 2 | Retry with exponential backoff on Duo Chat API (429, 5xx) | `invoke_duo_agent.py` |
| 3 | Retry with exponential backoff on GitLab REST API | `open_migration_mr.py` |
| 4 | Fixed shell injection risk — `--content-file` reads from disk instead of `$(cat ...)` | `open_migration_mr.py`, `.gitlab-ci.yml` |
| 5 | Multi-block Bicep extraction (model may split across fenced blocks) | `invoke_duo_agent.py` |
| 6 | Upsert commit action — create → fallback to update on 409 | `open_migration_mr.py` |
| 7 | Created `.gitignore` (excludes `generated/`, `__pycache__/`, `.DS_Store`, IDE files) | `.gitignore` (new) |
| 8 | Clarified prompt template `{{project_context}}` format | `pushtobicep_architect.md` |
| 9 | Fixed deprecated `next export` in portfolio site (unrelated, not pushed) | `next.config.js`, `package.json` |
| 10 | Removed stray `a.scpt` binary (accidental commit) | `a.scpt` (deleted) |

### 2. Reference & Naming Audit (8 fixes)

- Renamed `gitlab-ci.yml` → `.gitlab-ci.yml` (GitLab requires the leading dot)
- Renamed `azure_migration_architect.md` → `pushtobicep_architect.md` (naming consistency)
- Fixed `agent-config.yml` env var names (`GITLAB_TOKEN` → `GITLAB_API_TOKEN`, `GITLAB_PROJECT_ID` → `CI_PROJECT_ID`)
- Updated all cross-references in `agent-config.yml`, `invoke_duo_agent.py`, and `README.md`
- Fixed stale docstring in `open_migration_mr.py`
- Updated README file tree to match actual directory structure

### 3. CI Pipeline Bug Fixes (3 bugs)

| Bug | Fix |
|---|---|
| Alpine image has no `git` — `git diff` fails in detect stage | Added `apk add --no-cache git` |
| `CI_COMMIT_BEFORE_SHA` is all zeros on first push to new branch | Falls back to `origin/$CI_DEFAULT_BRANCH` |
| Stale comment said "Azure Migration Architect" | Updated to "PushToBicep Architect" |

### 4. Test Infrastructure

- `test_multitier_app.tf` — Realistic 8-resource AWS stack (ECS Fargate, ALB, RDS PostgreSQL, S3, ElastiCache Redis, CloudWatch, SNS, VPC) named "Contoso Orders"
- `test_Dockerfile` — Node.js multi-stage build with healthcheck
- `tests/test_local.py` — 33 unit tests covering template loading, prompt building, bicep extraction (single/multi/fallback), CLI parsing, env var validation, content-file reads
- `tests/test_e2e.py` — Full 3-stage pipeline simulation with mocked API response

### 5. Documentation

- Rewrote `README.md` with ASCII art diagrams, visual pipeline flow, repo structure box, roadmap table, and reliability section
- Added "Stress-Test with a Real-World Config" section documenting the Contoso Orders test flow

### By the Numbers

| Metric | Value |
|---|---|
| Commits | 6 |
| Files changed | 10 |
| Lines added | 855 |
| Lines removed | 175 |
| Unit tests | 33 (all passing) |
| E2E stages tested | 3 (all passing) |
| External dependencies | 0 (stdlib only) |

---

## Current State

```
  STATUS          DETAIL
  ─────────────   ─────────────────────────────────────────────
  Code            ✔ Complete — all scripts, CI, prompt, config
  Tests           ✔ Passing — 33 unit + 3-stage e2e (offline)
  GitHub          ✔ Pushed — main @ e85d510
  Uncommitted     ⚠ tests/ directory (test_local.py, test_e2e.py)
  Live API test   ✘ Blocked — waiting on GitLab Education approval
  Portfolio site  ⚠ Local fixes only (next.config.js, package.json) — not pushed
```

### Blocking Item

**GitLab for Education application** — submitted Mar 1 via `@tufts.edu` email. Approval typically takes 1–3 business days. Once approved:
1. Enable Duo Pro under group settings
2. Set `GITLAB_API_TOKEN` as a CI/CD variable
3. Push the test config → the pipeline runs end-to-end against the live Duo Chat API

---

## What's Coming Next

### Immediate (when you return)

- [ ] Commit `tests/` directory and push
- [ ] Check GitLab Education approval status
- [ ] Once approved: enable Duo Pro, set CI vars, run live pipeline
- [ ] Capture the generated Bicep output as `examples/generated_contoso_orders.bicep`
- [ ] Record a short demo (push → pipeline → MR with Bicep + cost estimate)

### Short-Term Enhancements

- [ ] GCP → Azure resource mappings in the prompt
- [ ] `az bicep build` validation step in CI (syntax-check generated Bicep before committing)
- [ ] Incremental MR diffs (update existing MR instead of creating a new one each time)
- [ ] Azure Retail Prices API integration for live cost estimates (replace static table)

### Medium-Term

- [ ] Policy guardrails (reject non-compliant SKUs or missing encryption)
- [ ] CODEOWNERS routing (auto-assign reviewers based on resource type)
- [ ] Slack/Teams notification on MR creation
- [ ] Support for Pulumi and AWS CDK input formats

---

## North Star

The vision beyond this hackathon is a **universal infrastructure migration agent** that lives in the CI pipeline of any Git repository:

1. **Any cloud → Azure**: Not just AWS Terraform, but GCP, multi-cloud, and any IaC format (Pulumi, CDK, CloudFormation, Docker Compose)
2. **Policy-aware**: Enforces organizational standards (encryption, network isolation, naming conventions) before the code even hits a reviewer
3. **Cost-intelligent**: Queries live Azure pricing APIs and compares against the source cloud spend — the MR shows not just "what it costs" but "what you save"
4. **Self-improving**: Feeds merge outcomes (approved vs. rejected, reviewer comments) back into the prompt to improve future generations
5. **Zero-touch migration at scale**: A platform team points it at 50 repos, and 50 MRs appear — each with valid Bicep, a cost delta, and a deployment command

The core insight: **cloud migrations fail not because they're hard, but because they're tedious**. Every manual step is a place where momentum dies. An agent that collapses "detect → translate → estimate → propose" into a single pipeline stage removes the tedium entirely and lets engineers focus on the decisions that actually matter.

---

*Last updated: March 6, 2026*
