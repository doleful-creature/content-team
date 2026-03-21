#!/usr/bin/env python3
"""
INWIGO Campaign Architect Agent
--------------------------------
Plans and documents complete marketing campaigns with full content calendars,
influencer strategy, KPIs, and execution checklists.

Usage:
    python agents/campaign_architect.py --type launch --timeline "Q2 2026" --weeks 6
    python agents/campaign_architect.py --type halloween-event --timeline "Oct 2026" --weeks 4 --goal "community + retention"
    python agents/campaign_architect.py --type pre-launch --timeline "Starting Jan 15" --weeks 8
    python agents/campaign_architect.py --help

Requirements:
    ANTHROPIC_API_KEY environment variable must be set.
    pip install -r requirements.txt
"""

import anthropic
import argparse
import os
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).parent.parent


def load_context() -> dict[str, str]:
    """Load all context files."""
    contexts = {}
    context_files = ["brand_kit.md", "game_facts.md", "audience_personas.md"]

    for fname in context_files:
        fpath = PROJECT_ROOT / "context" / fname
        if fpath.exists():
            contexts[fname] = fpath.read_text(encoding="utf-8")
        else:
            print(f"  ⚠️  Warning: {fname} not found — campaign plan may have gaps")
            contexts[fname] = f"[{fname} not found — please create context/{fname}]"

    return contexts


def save_campaign(content: str, campaign_name: str) -> Path:
    """Save the campaign plan to outputs/campaigns/."""
    output_dir = PROJECT_ROOT / "outputs" / "campaigns"
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    safe_name = (
        campaign_name.replace(" ", "_")
        .replace("/", "-")
        .replace(":", "")[:40]
    )
    fpath = output_dir / f"{timestamp}_{safe_name}.md"
    fpath.write_text(content, encoding="utf-8")
    return fpath


def build_prompt(
    campaign_type: str,
    timeline: str,
    weeks: int,
    goal: str,
    contexts: dict[str, str],
) -> str:
    """Build the campaign architect prompt."""
    return f"""You are a senior marketing strategist creating a complete campaign plan for INWIGO.

This plan is for a SOLO marketer. Every recommendation must be realistic for one person to execute.
Ruthless prioritization > comprehensive coverage.

## Context

### Brand Kit
{contexts['brand_kit.md']}

### Game Facts
{contexts['game_facts.md']}

### Audience Personas
{contexts['audience_personas.md']}

---

## Campaign Parameters

- **Type**: {campaign_type}
- **Timeline**: {timeline}
- **Duration**: {weeks} weeks
- **Primary Goal**: {goal}

---

## Deliverable: Complete Campaign Architecture

Create a comprehensive, immediately actionable campaign plan. This is the document the marketer
opens on Monday morning to know exactly what to do that week.

---

### 1. Campaign Overview

Create a clear summary table covering:
- Campaign name (evocative, specific — not "Launch Campaign")
- One-sentence campaign purpose
- Primary goal and secondary goal
- Full timeline with phase names
- Primary audience persona (Alex / Morgan / Jordan from the personas doc)
- Core message: the single thing you want people to remember
- Campaign-specific hashtag

Include a "Solo Marketer Reality Check" section: what 3 things matter most, and what to skip.

---

### 2. Strategic Foundation

Cover:
- The creative territory: what does every piece of content feel/look like?
- Three creative angles to test (different executions of the same core message)
- The ONE hero content piece this campaign builds toward (the centerpiece)
- Why this approach fits INWIGO's audience and brand

---

### 3. Phase-by-Phase Plan

Plan all {weeks} weeks in phases (group weeks into 2-3 phases as makes sense for the campaign type).

For each phase:
- Phase name and week range
- Phase goal (what changes in audience awareness/intent by end of this phase)
- Primary channels to focus on (which 2-3 get most energy)
- Key message for this phase
- Content cadence table (platform × frequency × content types)
- 3-5 must-create pieces for this phase (specific, not generic)
- Phase milestone/trigger (what marks success/end of this phase)

---

### 4. Complete Content Calendar

Create a detailed, week-by-week content calendar.

| Week | Date | Platform | Content Type | Topic / Angle | Format | Notes |
|------|------|----------|-------------|--------------|--------|-------|

Fill in ALL {weeks} weeks. At minimum 3-5 pieces per week across platforms.
For pieces dependent on game events or assets not yet confirmed, mark as "pending [trigger]".
Specific topics are better than generic ones (e.g., "Behind the scenes: how we made the funhouse mirrors" vs "Dev content").

---

### 5. Influencer & Press Strategy

**Target Hit List Template:**

| Priority | Handle / Name | Platform | Est. Audience | Why INWIGO Fits | Outreach Week | Status |
|----------|--------------|---------|--------------|-----------------|---------------|--------|
| Tier 1 | [VR creator, 100k+] | | | | | Not sent |
| Tier 1 | [Horror gaming creator] | | | | | Not sent |
| Tier 2 | [Mid-tier VR/indie creator] | | | | | Not sent |
| Tier 2 | [Cozy/aesthetic gaming creator] | | | | | Not sent |
| Tier 3 | [VR micro-influencer, authentic] | | | | | Not sent |
| Press | [VR/indie gaming publication] | | | | | Not sent |
| Press | [Gaming journalist covering VR] | | | | | Not sent |

Suggest specific types of creators/outlets that would work for this campaign type.

**Outreach timeline**: week-by-week plan for when to send what tier.

**Key assets to provide**: what goes in the pitch package for each tier.

---

### 6. Asset Production Checklist

| Asset | Format / Specs | Needed By | Status |
|-------|---------------|-----------|--------|
| | | Week X | [ ] |

Group assets as:
- **Must have before campaign starts**
- **Must have by Week X**
- **Nice to have**

---

### 7. KPIs & Tracking Dashboard

| Metric | Baseline | Week {weeks//2} Target | Final Target | Track In |
|--------|----------|----------------------|--------------|----------|

Include a "Weekly 15-min check-in" section: the 3 metrics to review every week.

---

### 8. Risk Register

| Risk | Likelihood (H/M/L) | Impact (H/M/L) | Mitigation |
|------|-------------------|----------------|------------|

Include at minimum:
- Campaign-type-specific risks
- Solo marketer burnout / capacity risks
- Asset/game readiness risks

---

### 9. Weekly Execution Checklist

A reusable Monday morning checklist for this campaign.

```
WEEK OF: ___________  (Week X of {weeks})

REVIEW (15 min):
[ ] Check metrics against targets
[ ] Note what worked / what didn't
[ ] Respond to community / press / creator messages

THIS WEEK'S CONTENT:
[ ] [Specific pieces from the calendar — fill in each week]

THIS WEEK'S OUTREACH:
[ ] [Who to contact this week]

COMMUNITY:
[ ] [Engagement targets or community actions]

END OF WEEK:
[ ] Metrics logged?
[ ] Anything to carry forward?
[ ] Next week prep done?
```

---

### 10. Solo Marketer Priority Stack

Given this is one person executing everything:

**Do first (highest leverage):**
1. [Activity 1 — explain why it's the highest leverage]
2. [Activity 2]
3. [Activity 3]

**Do if time allows:**
- [Lower priority items]

**Skip for this campaign:**
- [Explicitly deprioritize channels or tactics that won't move the needle for this specific campaign]

**The single metric that matters most**: [If you could only watch one number, it's ___ because ___]
"""


def generate_campaign(
    campaign_type: str,
    timeline: str,
    weeks: int,
    goal: str,
    client: anthropic.Anthropic,
) -> str:
    """Generate the campaign plan using Claude with streaming."""
    contexts = load_context()

    prompt = build_prompt(campaign_type, timeline, weeks, goal, contexts)

    print(f"\n{'='*60}")
    print(f"  🎪 INWIGO Campaign Architect")
    print(f"{'='*60}")
    print(f"  Type:     {campaign_type}")
    print(f"  Timeline: {timeline}")
    print(f"  Duration: {weeks} weeks")
    print(f"  Goal:     {goal}")
    print(f"  Model:    claude-opus-4-6 (adaptive thinking)")
    print(f"{'='*60}\n")
    print("Architecting campaign... (this takes 2-3 minutes for a full plan)\n")
    print("-" * 60)

    full_response = ""

    with client.messages.stream(
        model="claude-opus-4-6",
        max_tokens=10000,
        thinking={"type": "adaptive"},
        system=(
            "You are a senior marketing strategist who specializes in indie game launches. "
            "You create practical, opinionated campaign plans for small teams. "
            "You prioritize ruthlessly and are specific — no generic advice. "
            "Every recommendation should be something a solo marketer can actually execute."
        ),
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)
            full_response += text

    print("\n" + "-" * 60)
    return full_response


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a complete INWIGO marketing campaign plan.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python agents/campaign_architect.py --type launch --timeline "Q2 2026" --weeks 6
  python agents/campaign_architect.py --type halloween-event --timeline "Oct 2026" --weeks 4
  python agents/campaign_architect.py --type pre-launch --timeline "Starting Jan 15" --weeks 8 --goal "wishlist growth"
  python agents/campaign_architect.py --type demo-release --timeline "March 2026" --weeks 3 --goal "playtest signups"
        """,
    )
    parser.add_argument(
        "--type",
        required=True,
        help=(
            "Campaign type: launch, pre-launch, halloween-event, demo-release, "
            "community-building, post-launch, update-announcement"
        ),
    )
    parser.add_argument(
        "--timeline",
        required=True,
        help='Campaign timeline (e.g., "Q2 2026", "Oct 2026", "Starting Jan 15 2026")',
    )
    parser.add_argument(
        "--weeks",
        type=int,
        default=6,
        help="Campaign duration in weeks (default: 6)",
    )
    parser.add_argument(
        "--goal",
        default="awareness and wishlists",
        help='Primary campaign goal (default: "awareness and wishlists")',
    )
    args = parser.parse_args()

    # Validate
    if args.weeks < 1 or args.weeks > 24:
        print("❌ Error: --weeks must be between 1 and 24")
        sys.exit(1)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("\n❌ Error: ANTHROPIC_API_KEY environment variable is not set.")
        print("   Set it with: export ANTHROPIC_API_KEY='your-key-here'")
        print("   Get a key at: https://console.anthropic.com/")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    campaign_name = f"{args.type}-{args.weeks}wk"

    # Generate
    content = generate_campaign(
        campaign_type=args.type,
        timeline=args.timeline,
        weeks=args.weeks,
        goal=args.goal,
        client=client,
    )

    # Build file with metadata header
    header = f"""---
generated: {datetime.now().isoformat()}
campaign_type: {args.type}
timeline: {args.timeline}
weeks: {args.weeks}
goal: {args.goal}
model: claude-opus-4-6
---

# INWIGO Campaign Plan: {args.type.replace("-", " ").title()}
**Timeline**: {args.timeline} | **Duration**: {args.weeks} weeks | **Goal**: {args.goal}

*This plan was generated by the INWIGO Campaign Architect. Review and customize all sections,
especially the influencer/press hit list (requires your own research) and asset checklist
(confirm what you actually have ready).*

---

"""
    full_content = header + content

    # Save
    saved_path = save_campaign(full_content, campaign_name)

    print(f"\n{'='*60}")
    print(f"  ✅ Campaign plan saved!")
    print(f"{'='*60}")
    print(f"  File: {saved_path.relative_to(PROJECT_ROOT)}")
    print(f"\n  Next steps:")
    print(f"  1. Fill in the influencer hit list with real research")
    print(f"  2. Confirm asset availability against the production checklist")
    print(f"  3. Customize the content calendar with your specific topics")
    print(f"  4. Run /social or /outreach to start generating specific content")
    print(f"  5. Fill in game_facts.md if you see [FILL IN] gaps in the plan")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
