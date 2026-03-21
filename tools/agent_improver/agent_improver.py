#!/usr/bin/env python3
"""
Agent Improver
--------------
Reviews Claude Code skills (.md) and Python agents (.py), then produces
a structured critique + improved rewrite. Tracks improvement history per
agent so you can measure progress over time.

Standalone tool — works on any Claude Code project. Point it at any file.

Usage:
    # Review a skill file
    python tools/agent_improver/agent_improver.py .claude/commands/social.md

    # Review a Python agent
    python tools/agent_improver/agent_improver.py agents/content_batch_agent.py

    # Review with sample output to evaluate quality
    python tools/agent_improver/agent_improver.py .claude/commands/social.md \\
        --sample outputs/batches/latest.md

    # Review with human feedback notes
    python tools/agent_improver/agent_improver.py .claude/commands/social.md \\
        --feedback "outputs are too generic, missing brand voice, hashtags wrong"

    # Review with both
    python tools/agent_improver/agent_improver.py .claude/commands/social.md \\
        --sample outputs/social/last_week.md \\
        --feedback "needs more carnival-specific imagery in copy"

    # Show history for a specific agent
    python tools/agent_improver/agent_improver.py .claude/commands/social.md --history

    # Apply the latest improvement (replaces the original file)
    python tools/agent_improver/agent_improver.py .claude/commands/social.md --apply

Requirements:
    ANTHROPIC_API_KEY must be set.
    pip install anthropic
"""

import anthropic
import argparse
import json
import os
import sys
import textwrap
from datetime import datetime
from pathlib import Path


# ── Configuration ────────────────────────────────────────────────────────────

TOOL_DIR = Path(__file__).parent
LOG_FILE = TOOL_DIR / "improvement_log.json"
IMPROVEMENTS_DIR = TOOL_DIR / "improvements"


# ── File type detection ───────────────────────────────────────────────────────

def detect_file_type(path: Path) -> str:
    """Determine whether the target is a skill (.md) or a Python agent (.py)."""
    suffix = path.suffix.lower()
    if suffix == ".md":
        # Distinguish Claude Code skills from other .md files
        commands_indicators = [".claude/commands", "commands/"]
        if any(part in str(path) for part in commands_indicators):
            return "skill"
        return "document"
    elif suffix == ".py":
        return "agent"
    return "unknown"


# ── Context loading ───────────────────────────────────────────────────────────

def find_project_root(start: Path) -> Path | None:
    """Walk up from the target file to find a CLAUDE.md or .git directory."""
    current = start.resolve().parent
    for _ in range(10):  # max 10 levels up
        if (current / "CLAUDE.md").exists() or (current / ".git").exists():
            return current
        if current.parent == current:
            break
        current = current.parent
    return None


def load_project_context(target_path: Path) -> str:
    """Load CLAUDE.md if present — gives the reviewer project-specific context."""
    project_root = find_project_root(target_path)
    if project_root is None:
        return ""

    claude_md = project_root / "CLAUDE.md"
    if claude_md.exists():
        content = claude_md.read_text(encoding="utf-8")
        return f"\n## Project Context (from CLAUDE.md)\n\n{content}\n"

    return ""


def load_related_files(target_path: Path, file_type: str) -> str:
    """For skills, look for context files referenced in the skill."""
    if file_type != "skill":
        return ""

    project_root = find_project_root(target_path)
    if project_root is None:
        return ""

    # Find @-referenced files in the skill
    content = target_path.read_text(encoding="utf-8")
    referenced_context = []

    for line in content.splitlines():
        line = line.strip()
        if line.startswith("@"):
            ref_path = project_root / line[1:]
            if ref_path.exists():
                ref_content = ref_path.read_text(encoding="utf-8")
                # Truncate very long context files to avoid token overload
                if len(ref_content) > 3000:
                    ref_content = ref_content[:3000] + "\n\n[... truncated for review ...]"
                referenced_context.append(f"### Referenced file: {line[1:]}\n\n{ref_content}")

    if referenced_context:
        return "\n## Files Referenced in This Skill\n\n" + "\n\n---\n\n".join(referenced_context)
    return ""


# ── Improvement log ───────────────────────────────────────────────────────────

def load_log() -> dict:
    """Load the improvement history log."""
    if LOG_FILE.exists():
        try:
            return json.loads(LOG_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def save_log(log: dict) -> None:
    """Save the improvement history log."""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    LOG_FILE.write_text(json.dumps(log, indent=2, ensure_ascii=False), encoding="utf-8")


def log_review(
    target_path: Path,
    version: int,
    critique_path: Path,
    improved_path: Path,
    feedback: str | None,
    had_sample: bool,
) -> None:
    """Record a review in the improvement log."""
    log = load_log()
    key = str(target_path.resolve())

    if key not in log:
        log[key] = {"path": str(target_path), "reviews": []}

    log[key]["reviews"].append({
        "version": version,
        "timestamp": datetime.now().isoformat(),
        "critique": str(critique_path),
        "improved": str(improved_path),
        "had_sample_output": had_sample,
        "had_feedback": bool(feedback),
        "feedback_summary": (feedback[:200] if feedback else None),
    })

    save_log(log)


def get_version(target_path: Path) -> int:
    """Get the next version number for a given agent."""
    log = load_log()
    key = str(target_path.resolve())
    if key in log and log[key]["reviews"]:
        return log[key]["reviews"][-1]["version"] + 1
    return 1


def show_history(target_path: Path) -> None:
    """Print the review history for a target file."""
    log = load_log()
    key = str(target_path.resolve())

    if key not in log or not log[key]["reviews"]:
        print(f"\nNo review history found for: {target_path}")
        print("Run a review first to start tracking improvements.")
        return

    reviews = log[key]["reviews"]
    print(f"\n📋 Review History: {target_path.name}")
    print(f"   {len(reviews)} review(s) on record\n")

    for r in reviews:
        ts = datetime.fromisoformat(r["timestamp"]).strftime("%b %d %Y, %H:%M")
        markers = []
        if r["had_sample_output"]:
            markers.append("sample output")
        if r["had_feedback"]:
            markers.append(f'feedback: "{r["feedback_summary"]}"')
        marker_str = f" [{', '.join(markers)}]" if markers else ""

        print(f"  v{r['version']} — {ts}{marker_str}")
        print(f"    Critique:  {Path(r['critique']).name}")
        print(f"    Improved:  {Path(r['improved']).name}")

    print()


def apply_latest(target_path: Path) -> None:
    """Replace the target file with the most recent improved version."""
    log = load_log()
    key = str(target_path.resolve())

    if key not in log or not log[key]["reviews"]:
        print(f"\n❌ No review history found for: {target_path}")
        return

    latest = log[key]["reviews"][-1]
    improved_path = Path(latest["improved"])

    if not improved_path.exists():
        print(f"\n❌ Improved file not found: {improved_path}")
        return

    # Back up the current file first
    backup_path = target_path.with_suffix(target_path.suffix + ".bak")
    backup_path.write_text(target_path.read_text(encoding="utf-8"), encoding="utf-8")

    # Apply
    target_path.write_text(improved_path.read_text(encoding="utf-8"), encoding="utf-8")

    print(f"\n✅ Applied v{latest['version']} improvement to: {target_path}")
    print(f"   Original backed up to: {backup_path}")
    print(f"   To undo: mv {backup_path} {target_path}")


# ── Prompt building ───────────────────────────────────────────────────────────

SKILL_REVIEW_PROMPT = """\
You are an expert prompt engineer and Claude Code specialist. Your job is to review a Claude Code
custom skill (a slash command stored as a .md file in .claude/commands/) and produce:
1. A detailed, actionable critique
2. An improved version of the skill, ready to deploy

You evaluate across three dimensions: prompt engineering quality, output format quality,
and (if provided) actual output quality from sample runs.

## Target Skill

**File**: {filename}

```markdown
{content}
```
{project_context}
{related_files}
{sample_section}
{feedback_section}

---

## Your Review

### PART 1: CRITIQUE

Structure your critique as follows:

#### Overall Assessment
Score the skill 1-10 on each dimension, then give an overall score:
- **Prompt Clarity** (1-10): Is Claude unambiguous about what to do?
- **Context Loading** (1-10): Does it pull in the right context, well-organized?
- **Output Specification** (1-10): Is the desired output format precisely and completely defined?
- **Role/Persona** (1-10): Is there a clear, effective role/persona for Claude?
- **Edge Case Handling** (1-10): Are unusual or minimal inputs handled?
- **Quality Criteria** (1-10): Does the skill have built-in quality checks?
{output_quality_criterion}
- **Overall Score** (1-10):

#### Issues Found
For each issue: state the problem, its impact, and a specific fix.

**[Issue 1 — severity: high/medium/low]**: [What the problem is]
- Impact: [What goes wrong when this is an issue]
- Fix: [Specific change to make]

[Continue for all issues found — be thorough but prioritize]

#### What's Working Well
[2-5 specific things this skill does right — be genuine, not generic]

#### Improvement Priorities
Ranked list of the 3 most impactful changes to make:
1. [Highest impact change]
2. [Second highest]
3. [Third]

---

### PART 2: IMPROVED VERSION

Write the complete, improved skill file. This should be a drop-in replacement.

Apply ALL the fixes from your critique. The improved version should:
- Fix every high-severity issue
- Fix all medium-severity issues where possible
- Apply prompt engineering best practices
- Preserve what was working well
- Be tested mentally: imagine 5 different ways a user might invoke this skill — does the improved version handle all of them well?

Write the full file between the markers below:

<<<IMPROVED_START>>>
[Complete improved .md file content here — this will be extracted and saved as a separate file]
<<<IMPROVED_END>>>

---

### PART 3: CHANGELOG

Brief summary of the key changes made, for the improvement log:
- [Change 1]
- [Change 2]
- [Change 3]
[...]
"""


AGENT_REVIEW_PROMPT = """\
You are an expert Python developer and Claude API specialist. Your job is to review a Python
agent that uses the Anthropic SDK and produce:
1. A detailed, actionable critique
2. An improved version of the agent, ready to deploy

You evaluate across four dimensions: prompt engineering quality (the prompts embedded in the code),
Python code quality, Anthropic API usage best practices, and (if provided) actual output quality.

## Target Agent

**File**: {filename}

```python
{content}
```
{project_context}
{sample_section}
{feedback_section}

---

## Your Review

### PART 1: CRITIQUE

#### Overall Assessment
- **System Prompt Quality** (1-10): Is the system prompt clear, well-scoped, appropriate?
- **User Prompt Quality** (1-10): Is the main prompt well-structured and complete?
- **API Usage** (1-10): Correct model, thinking config, streaming, max_tokens, error handling?
- **Context Management** (1-10): Does it load and pass the right context?
- **Code Quality** (1-10): CLI design, error handling, output organization, maintainability?
- **Output Quality** (1-10): Are outputs well-structured, named, and organized?
{output_quality_criterion}
- **Overall Score** (1-10):

#### Issues Found
For each: problem, impact, specific fix.

**[Issue 1 — severity: high/medium/low]**: [What the problem is]
- Impact: [What goes wrong]
- Fix: [Specific change]

[Continue for all issues]

#### What's Working Well
[2-5 genuine strengths]

#### Improvement Priorities
1. [Highest impact change]
2. [Second]
3. [Third]

---

### PART 2: IMPROVED VERSION

Write the complete improved Python file. Drop-in replacement.

Apply all fixes. The improved version should:
- Fix every high-severity issue
- Apply Anthropic SDK best practices (adaptive thinking, streaming, error handling)
- Improve prompt quality where identified
- Maintain CLI usability
- Be mentally tested: would it fail on edge cases the original would fail on?

<<<IMPROVED_START>>>
[Complete improved .py file content here]
<<<IMPROVED_END>>>

---

### PART 3: CHANGELOG
- [Change 1]
- [Change 2]
[...]
"""


def build_prompt(
    target_path: Path,
    file_type: str,
    sample_output: str | None,
    feedback: str | None,
    project_context: str,
    related_files: str,
) -> str:
    """Build the full review prompt."""
    content = target_path.read_text(encoding="utf-8")

    sample_section = ""
    if sample_output:
        truncated = sample_output[:4000] + "\n\n[... truncated ...]" if len(sample_output) > 4000 else sample_output
        sample_section = f"\n## Sample Output to Evaluate\n\nThis is actual output produced by this skill/agent:\n\n```\n{truncated}\n```\n"

    feedback_section = ""
    if feedback:
        feedback_section = f"\n## Human Feedback\n\nThe person using this skill provided the following notes:\n\n> {feedback}\n\nUse this feedback to calibrate your critique — these are observed real-world issues.\n"

    output_quality_criterion = (
        "- **Output Quality** (1-10): Based on the sample output provided, how good is actual output?\n"
        if sample_output
        else "- **Output Quality** (1-10): N/A — no sample provided (score as N/A)\n"
    )

    template = SKILL_REVIEW_PROMPT if file_type == "skill" else AGENT_REVIEW_PROMPT

    return template.format(
        filename=target_path.name,
        content=content,
        project_context=project_context,
        related_files=related_files,
        sample_section=sample_section,
        feedback_section=feedback_section,
        output_quality_criterion=output_quality_criterion,
    )


# ── Output extraction ─────────────────────────────────────────────────────────

def extract_improved(response_text: str) -> str | None:
    """Extract the improved file content from between the markers."""
    start_marker = "<<<IMPROVED_START>>>"
    end_marker = "<<<IMPROVED_END>>>"

    start_idx = response_text.find(start_marker)
    end_idx = response_text.find(end_marker)

    if start_idx == -1 or end_idx == -1:
        return None

    improved = response_text[start_idx + len(start_marker):end_idx].strip()

    # Strip code fences if the model wrapped the content
    if improved.startswith("```"):
        first_newline = improved.find("\n")
        if first_newline != -1:
            improved = improved[first_newline + 1:]
        if improved.endswith("```"):
            improved = improved[:-3].rstrip()

    return improved


# ── Save outputs ──────────────────────────────────────────────────────────────

def save_outputs(
    target_path: Path,
    file_type: str,
    version: int,
    critique_text: str,
    improved_content: str | None,
) -> tuple[Path, Path | None]:
    """Save critique and improved file to the improvements directory."""
    # Agent-specific subdirectory
    agent_dir = IMPROVEMENTS_DIR / target_path.stem
    agent_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    prefix = f"v{version}_{timestamp}"

    # Save critique
    critique_path = agent_dir / f"{prefix}_critique.md"
    critique_path.write_text(critique_text, encoding="utf-8")

    # Save improved version
    improved_path = None
    if improved_content:
        ext = target_path.suffix
        improved_path = agent_dir / f"{prefix}_improved{ext}"
        improved_path.write_text(improved_content, encoding="utf-8")

    return critique_path, improved_path


# ── Main review flow ──────────────────────────────────────────────────────────

def run_review(
    target_path: Path,
    file_type: str,
    sample_output: str | None,
    feedback: str | None,
    client: anthropic.Anthropic,
) -> None:
    """Run the full review and save outputs."""
    version = get_version(target_path)
    project_context = load_project_context(target_path)
    related_files = load_related_files(target_path, file_type)

    prompt = build_prompt(
        target_path, file_type, sample_output, feedback, project_context, related_files
    )

    type_label = "Skill" if file_type == "skill" else "Python Agent"

    print(f"\n{'='*60}")
    print(f"  🔍 Agent Improver")
    print(f"{'='*60}")
    print(f"  Target:  {target_path}")
    print(f"  Type:    {type_label}")
    print(f"  Version: v{version}")
    if sample_output:
        print(f"  Sample:  {len(sample_output)} chars of output provided")
    if feedback:
        print(f"  Feedback: \"{feedback[:60]}{'...' if len(feedback) > 60 else ''}\"")
    print(f"  Model:   claude-opus-4-6 (adaptive thinking)")
    print(f"{'='*60}\n")
    print("Analyzing... (30-90 seconds)\n")
    print("-" * 60)

    full_response = ""

    with client.messages.stream(
        model="claude-opus-4-6",
        max_tokens=8000,
        thinking={"type": "adaptive"},
        system=(
            "You are a world-class prompt engineer and Claude API expert. "
            "You give precise, opinionated, actionable critique — not vague suggestions. "
            "Every issue you identify comes with a specific, implementable fix. "
            "Your rewrites are better than the original, not just differently formatted."
        ),
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)
            full_response += text

    print("\n" + "-" * 60)

    # Extract improved version
    improved_content = extract_improved(full_response)
    if not improved_content:
        print("\n⚠️  Could not extract improved file from response.")
        print("   The critique is still saved. You may need to copy the improved version manually.")

    # Save outputs
    critique_path, improved_path = save_outputs(
        target_path, file_type, version, full_response, improved_content
    )

    # Log the review
    log_review(
        target_path, version, critique_path, improved_path or critique_path,
        feedback, bool(sample_output)
    )

    # Summary
    print(f"\n{'='*60}")
    print(f"  ✅ Review complete (v{version})")
    print(f"{'='*60}")
    print(f"  Critique:  {critique_path.relative_to(Path.cwd()) if critique_path.is_relative_to(Path.cwd()) else critique_path}")
    if improved_path:
        print(f"  Improved:  {improved_path.relative_to(Path.cwd()) if improved_path.is_relative_to(Path.cwd()) else improved_path}")
        print(f"\n  To apply the improvement:")
        print(f"    python {__file__} {target_path} --apply")
    print(f"\n  To view history:")
    print(f"    python {__file__} {target_path} --history")
    print(f"{'='*60}\n")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Review and improve Claude Code skills and Python agents.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
            Examples:
              # Review a skill
              python tools/agent_improver/agent_improver.py .claude/commands/social.md

              # Review a Python agent with a sample output
              python tools/agent_improver/agent_improver.py agents/content_batch_agent.py \\
                  --sample outputs/batches/20241014_social.md

              # Review with human feedback
              python tools/agent_improver/agent_improver.py .claude/commands/social.md \\
                  --feedback "hashtags are wrong, missing carnival imagery in copy"

              # View improvement history
              python tools/agent_improver/agent_improver.py .claude/commands/social.md --history

              # Apply the latest improvement (overwrites original, backs up)
              python tools/agent_improver/agent_improver.py .claude/commands/social.md --apply
        """),
    )
    parser.add_argument("target", help="Path to the skill (.md) or agent (.py) to review")
    parser.add_argument(
        "--sample",
        metavar="FILE",
        help="Path to a sample output file produced by this skill/agent",
    )
    parser.add_argument(
        "--feedback",
        metavar="TEXT",
        help='Human feedback notes (e.g., "outputs too generic, wrong hashtags")',
    )
    parser.add_argument(
        "--history",
        action="store_true",
        help="Show review history for this agent without running a new review",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply the most recent improved version (backs up the original)",
    )
    args = parser.parse_args()

    target_path = Path(args.target)

    if not target_path.exists():
        print(f"\n❌ File not found: {target_path}")
        sys.exit(1)

    # History mode
    if args.history:
        show_history(target_path)
        return

    # Apply mode
    if args.apply:
        apply_latest(target_path)
        return

    # Detect file type
    file_type = detect_file_type(target_path)
    if file_type not in ("skill", "agent"):
        print(f"\n❌ Unsupported file type: {target_path.suffix}")
        print("   Supported: .md (Claude Code skills) and .py (Python agents)")
        sys.exit(1)

    # Load sample output if provided
    sample_output = None
    if args.sample:
        sample_path = Path(args.sample)
        if not sample_path.exists():
            print(f"\n❌ Sample file not found: {sample_path}")
            sys.exit(1)
        sample_output = sample_path.read_text(encoding="utf-8")

    # Validate API key
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("\n❌ ANTHROPIC_API_KEY environment variable is not set.")
        print("   export ANTHROPIC_API_KEY='your-key'")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    run_review(
        target_path=target_path,
        file_type=file_type,
        sample_output=sample_output,
        feedback=args.feedback,
        client=client,
    )


if __name__ == "__main__":
    main()
