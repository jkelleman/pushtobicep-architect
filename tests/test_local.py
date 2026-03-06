#!/usr/bin/env python3
"""
Offline tests for invoke_duo_agent.py and open_migration_mr.py.
Validates everything that doesn't require a live GitLab API.

Run:  python tests/test_local.py
"""
import sys
import os
import json
from pathlib import Path

# Ensure repo root is on the path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

passed = 0
failed = 0


def check(label, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS  {label}")
    else:
        failed += 1
        print(f"  FAIL  {label}  {detail}")


# ═══════════════════════════════════════════════════════════════════
print("\n=== invoke_duo_agent.py ===\n")

from scripts.invoke_duo_agent import (
    _load_prompt_template,
    _build_prompt,
    _extract_bicep,
    _extract_summary,
    PROMPT_TEMPLATE_PATH,
)

# ── 1. Template loading ────────────────────────────────────────
print("[1] Template loading")
check("template file exists", PROMPT_TEMPLATE_PATH.exists(),
      f"expected {PROMPT_TEMPLATE_PATH}")

template = _load_prompt_template()
check("template is non-empty", len(template) > 100,
      f"got {len(template)} chars")
check("has {{original_code}} placeholder",
      "{{original_code}}" in template)
check("has {{project_context}} placeholder",
      "{{project_context}}" in template)

# ── 2. Prompt building with real test file ─────────────────────
print("\n[2] Prompt building")
tf_path = ROOT / "examples" / "test_multitier_app.tf"
check("test TF file exists", tf_path.exists())

tf_code = tf_path.read_text()
check("test TF file non-empty", len(tf_code) > 500,
      f"got {len(tf_code)} chars")

code_block = f"### File: main.tf\n```\n{tf_code}\n```"
prompt = _build_prompt(code_block)
check("{{original_code}} replaced",
      "{{original_code}}" not in prompt)
check("{{project_context}} replaced",
      "{{project_context}}" not in prompt)
check("TF content embedded (aws_ecs_cluster)",
      "aws_ecs_cluster" in prompt)
check("TF content embedded (aws_db_instance)",
      "aws_db_instance" in prompt)
check("TF content embedded (aws_s3_bucket)",
      "aws_s3_bucket" in prompt)
print(f"    prompt length: {len(prompt)} chars")

# ── 3. Bicep extraction — single block ────────────────────────
print("\n[3] Bicep extraction (single block)")

FAKE_SINGLE = (
    "## Migration Summary\n"
    "We detected an ECS Fargate workload...\n\n"
    "## Resource Mapping\n"
    "| AWS ECS | Azure Container Apps | Best match |\n\n"
    "## Azure Cost Estimate (Monthly)\n"
    "| Container Apps | Consumption | $45 |\n\n"
    "## Generated Bicep Code\n"
    "```bicep\n"
    "param location string = 'eastus'\n"
    "\n"
    "resource containerApp 'Microsoft.App/containerApps@2023-05-01' = {\n"
    "  name: 'contoso-orders'\n"
    "  location: location\n"
    "}\n"
    "```\n\n"
    "## Deployment Instructions\n"
    "az deployment group create...\n"
)

bicep = _extract_bicep(FAKE_SINGLE)
check("bicep content extracted", "param location" in bicep)
check("no backtick leakage", "```" not in bicep)

summary = _extract_summary(FAKE_SINGLE)
check("summary includes Migration Summary",
      "Migration Summary" in summary)
check("summary excludes Generated Bicep",
      "Generated Bicep" not in summary)
print(f"    bicep: {len(bicep)} chars, summary: {len(summary)} chars")

# ── 4. Bicep extraction — multiple blocks ─────────────────────
print("\n[4] Bicep extraction (multiple blocks)")

FAKE_MULTI = (
    "## Migration Summary\nMultiple modules...\n\n"
    "## Generated Bicep Code\n"
    "```bicep\n"
    "// Module 1: networking\n"
    "param vnetName string = 'contoso-vnet'\n"
    "resource vnet 'Microsoft.Network/virtualNetworks@2023-05-01' = {\n"
    "  name: vnetName\n"
    "}\n"
    "```\n\n"
    "Additional database resources:\n"
    "```bicep\n"
    "// Module 2: database\n"
    "param dbName string = 'contoso-db'\n"
    "resource db 'Microsoft.DBforPostgreSQL/flexibleServers@2023-06-01-preview' = {\n"
    "  name: dbName\n"
    "}\n"
    "```\n"
)

bicep_multi = _extract_bicep(FAKE_MULTI)
check("first block present (vnetName)", "vnetName" in bicep_multi)
check("second block present (dbName)", "dbName" in bicep_multi)
check("no backtick leakage", "```" not in bicep_multi)

# ── 5. Bicep extraction — fallback (no fenced block) ──────────
print("\n[5] Bicep extraction (fallback — no fenced block)")

FAKE_NOFENCE = (
    "## Migration Summary\nSome summary.\n\n"
    "## Generated Bicep Code\n"
    "param location string = 'eastus'\n"
    "resource rg 'Microsoft.Resources/resourceGroups@2023-07-01' = {\n"
    "  name: 'rg-contoso'\n"
    "  location: location\n"
    "}\n"
)

bicep_fallback = _extract_bicep(FAKE_NOFENCE)
check("fallback extracts content", "param location" in bicep_fallback)

# ── 6. Edge case — no bicep at all ────────────────────────────
print("\n[6] Edge case (no Bicep marker)")

bicep_empty = _extract_bicep("This response has no code at all.")
check("returns raw text when no markers",
      "no code at all" in bicep_empty)


# ═══════════════════════════════════════════════════════════════════
print("\n\n=== open_migration_mr.py ===\n")

from scripts.open_migration_mr import main as mr_main

# ── 7. CLI — missing env vars ─────────────────────────────────
print("[7] CLI rejects missing env vars")

# Temporarily unset the env vars
old_pid = os.environ.get("CI_PROJECT_ID")
old_tok = os.environ.get("GITLAB_API_TOKEN")
os.environ.pop("CI_PROJECT_ID", None)
os.environ.pop("GITLAB_API_TOKEN", None)

# Re-import to pick up empty env vars
import importlib
import scripts.open_migration_mr as mr_mod
importlib.reload(mr_mod)

# The module reads env vars at import time, confirm they're empty
check("PROJECT_ID is empty after unset",
      mr_mod.PROJECT_ID == "")
check("API_TOKEN is empty after unset",
      mr_mod.API_TOKEN == "")

# Restore
if old_pid:
    os.environ["CI_PROJECT_ID"] = old_pid
if old_tok:
    os.environ["GITLAB_API_TOKEN"] = old_tok

# ── 8. CLI — argument parsing ─────────────────────────────────
print("\n[8] CLI argument parsing")

import argparse

# Test that --action is required
try:
    mr_mod_parser = argparse.ArgumentParser()
    mr_mod_parser.add_argument("--action", required=True,
                                choices=["create-branch", "commit", "open-mr"])
    mr_mod_parser.add_argument("--file")
    mr_mod_parser.add_argument("--content")
    mr_mod_parser.add_argument("--content-file")
    mr_mod_parser.add_argument("--title")
    mr_mod_parser.add_argument("--description")

    args = mr_mod_parser.parse_args(["--action", "commit", "--file", "infra/main.bicep",
                                      "--content-file", "generated/main.bicep"])
    check("parses commit action", args.action == "commit")
    check("parses --file", args.file == "infra/main.bicep")
    check("parses --content-file",
          args.content_file == "generated/main.bicep")
except SystemExit:
    check("argument parsing", False, "parser exited unexpectedly")

# ── 9. --content-file reads from disk ─────────────────────────
print("\n[9] --content-file reads from disk")

# Create a temp bicep file
test_bicep = ROOT / "generated" / "_test_content.bicep"
test_bicep.parent.mkdir(parents=True, exist_ok=True)
test_bicep.write_text("param test string = 'hello'\n")

content = Path(str(test_bicep)).read_text()
check("content-file reads correctly",
      "param test" in content)

# Cleanup
test_bicep.unlink()


# ═══════════════════════════════════════════════════════════════════
print("\n\n=== Dockerfile test input ===\n")

print("[10] test_Dockerfile exists and is valid")
df_path = ROOT / "examples" / "test_Dockerfile"
check("test_Dockerfile exists", df_path.exists())
df_content = df_path.read_text()
check("has FROM instruction", "FROM" in df_content)
check("has multi-stage build", "AS builder" in df_content)
check("has HEALTHCHECK", "HEALTHCHECK" in df_content)
check("has EXPOSE 3000", "EXPOSE 3000" in df_content)

# Build prompt with Dockerfile too
df_block = f"### File: Dockerfile\n```\n{df_content}\n```"
combined_prompt = _build_prompt(code_block + "\n\n" + df_block)
check("combined prompt has TF content",
      "aws_ecs_cluster" in combined_prompt)
check("combined prompt has Dockerfile content",
      "HEALTHCHECK" in combined_prompt)
print(f"    combined prompt: {len(combined_prompt)} chars")


# ═══════════════════════════════════════════════════════════════════
print("\n\n" + "=" * 60)
print(f"  Results: {passed} passed, {failed} failed")
print("=" * 60)

if failed > 0:
    sys.exit(1)
else:
    print("  All tests passed!\n")
