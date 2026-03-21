#!/usr/bin/env python3
"""
INWIGO Campaign Architect Agent
--------------------------------
Plans and documents complete marketing campaigns with full content calendars,
influencer strategy, KPIs, and execution checklists.

Usage:
    python agents/campaign_architect.py --type launch --timeline "Q2 2026" --weeks 6
    python agents/campaign_architect.py --type halloween-event --timeline "Oct 2026" --weeks 4 --goal "community + retention"
    python agents/campaign_architect.py --type pre-launch --timeline "Starting Jan 15" --weeks 8 --name "The Carnival Awakens"
    python agents/campaign_architect.py --type launch --timeline "Q2 2026" --weeks 6 --dry-run
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

VALID_CAMPAIGN_TYPES = [
    "launch", "pre-launch", "halloween-event", "demo-release",
    "community-building", "post-launch", "update-announcement",
]


def load_context() -> dict[str, str]:
    """Load all context files. Warns prominently if any are missing."""
    contexts = {}
    context_files = ["brand_kit.md", "game_facts.md", "audience_personas.md"]
    missing = []

    for fname in context_files:
        fpath = PROJECT_ROOT / "context" / fname
        if fpath.exists():
            content = fpath.read_text(encoding="utf-8")
            contexts[fname] = content
            fill_count = content.count("[FILL IN]")
            if fill_count > 0:
                print(f"  ⚠️  {fname}: {fill_count} [FILL IN] placeholder(s) found — "
                      f"campaign plan will note these gaps")
        else:
            missing.append(fname)
            print(f"  ❌ Warning: {fname} not found — campaign plan will have gaps")
            contexts[fname] = f"[{fname} not found — please create context/{fname}]"

    if missing:
        print(f"\n  ⚠️  {len(missing)} context file(s) missing. "
              f"Generated plan quality will be reduced.\n")

    return contexts


def save_campaign(content: str, filename: str, output_dir: Path | None = None) -> Path:
    """Save the campaign plan to outputs/campaigns/ or custom directory."""
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        fpath = output_dir / filename
    else:
        dest_dir = PROJECT_ROOT / "outputs" / "campaigns"
        dest_dir.mkdir(parents=True, exist_ok=True)
        fpath = dest_dir / filename
    fpath.write_text(content, encoding="utf-8")
    return fpath


def slugify(text: str, max_len: int = 20) -> str:
    """Create a URL/filename-safe slug, truncated at word boundaries."""
    slug = text.lower().replace(" ", "-").replace("/", "-").replace("_", "-")
    slug = "".join(c for c in slug if c.isalnum() or c == "-")
    if len(slug) > max_len:
        # Truncate at word boundary
        parts = slug.split("-")
        result = []
        current_len = 0
        for part in parts:
            addition = len(part) + (1 if result else 0)
            if current_len + addition > max_len:
                break
            result.append(part)
            current_len += addition
        slug = "-".join(result)
    return slug


def build_prompt(
    campaign_type: str,
    timeline: str,
    weeks: int,
    goal: str,
    campaign_name: str,
    contexts: dict[str, str],
) -> str:
    """Build the campaign architect prompt."""
    return f"""You are a senior marketing strategist creating a complete campaign plan for INWIGO.

This plan is for a SOLO marketer. Every recommendation must be realistic for one person to execute.
Ruthless prioritization > comprehensive coverage. Specific > generic, always.

## Context

### Brand Kit
{contexts['brand_kit.md']}

### Game Facts
{contexts['game_facts.md']}

### Audience Personas
{contexts['audience_personas.md']}

---

## Campaign Parameters

- **Campaign Name**: {campaign_name}
- **Type**: {campaign_type}
- **Timeline**: {timeline}
- **Duration**: {weeks} weeks
- **Primary Goal**: {goal}

---

## Deliverable: Complete Campaign Architecture

This is the document the marketer opens on Monday morning to know exactly what to do that week.
Be specific, opinionated, and practical. No generic advice.

**Output length note**: For campaigns 6+ weeks, you may abbreviate the content calendar from
Week 4 onward with a clear pattern description rather than generic row labels. Complete the
structure fully; depth matters more than exhaustive rows.

---

### 1. Campaign Overview

Create a summary table:
- Campaign name: {campaign_name}
- One-sentence campaign purpose
- Primary and secondary goals
- Full timeline with phase names
- Primary audience persona (Alex / Morgan / Jordan — name it and explain why they're primary)
- Core message: the single thing you want people to remember (1 sentence)
- Campaign hashtag (under 20 chars, unique, standalone-memorable — e.g., #CarnivalOpens)

Include a "Solo Marketer Reality Check": what 3 things matter most, and what to explicitly skip.

---

### 2. Strategic Foundation

- The creative territory: what does every piece of content feel/look like? (2-3 sentences)
- Three creative angles to test (specific executions — not just "be funny")
- The ONE hero content piece: name it specifically (not "a trailer" but "a 60-second TikTok series where players attempt a specific carnival challenge")
- Why this approach fits INWIGO's audience and brand for THIS campaign type

---

### 3. Phase-by-Phase Plan

Group {weeks} weeks into 2–3 phases. Name each phase for what it achieves.

For each phase:
- Phase name and week range
- Phase goal (what changes in audience awareness/intent)
- Primary channels (which 2–3 get most energy — be selective)
- Key message for this phase
- Content cadence table (platform × frequency × content types)
- 3–5 must-create pieces (SPECIFIC topics, not "a TikTok" but "TikTok: jump scare compilation with reaction overlay")
- Phase milestone/trigger

---

### 4. Complete Content Calendar

Minimum 4 rows per week. REAL topic names required — draw directly from the creative angles
in Section 2. "Behind the scenes: funhouse mirror art" is a topic. "Dev content" is not.

For pieces dependent on assets not yet confirmed, write "pending [specific trigger]".

For campaigns 6+ weeks: fill Weeks 1-3 fully; for Weeks 4+, describe the repeating pattern
(e.g., "Weeks 4-6 follow Week 3's cadence: 2x Twitter/week (hype + community), 1x TikTok
gameplay clip, 1x Discord update. Specific topics: [list 3-4 examples]").

| Week | Date | Platform | Content Type | Topic / Angle | Format | Notes |
|------|------|----------|-------------|--------------|--------|-------|

---

### 5. Influencer & Press Strategy

Calibrate to this campaign type:
- Launch → YouTube reviewers + Twitch streamers covering VR or horror co-op
- Halloween event → Short-form horror creators on TikTok + Instagram
- Community-building → Discord builders + VR micro-influencers + Reddit community figures
- Pre-launch → VR-focused creators who review upcoming releases

| Priority | Handle / Name | Platform | Est. Audience | Why INWIGO Fits | Outreach Week | Status |
|----------|--------------|---------|--------------|-----------------|---------------|--------|
| Tier 1 | [Specific creator type for THIS campaign] | | | | | Not sent |
| Tier 1 | [Second Tier 1 type] | | | | | Not sent |
| Tier 2 | [Mid-tier type] | | | | | Not sent |
| Tier 2 | [Second Tier 2 type] | | | | | Not sent |
| Tier 3 | [Micro-influencer type] | | | | | Not sent |
| Press | [Publication type for this campaign] | | | | | Not sent |

Outreach timeline: week-by-week plan for when to send each tier.
Key assets per pitch tier: what goes in the package for Tier 1 vs Tier 2 vs Press.

---

### 6. Asset Production Checklist

Group as: Must have before campaign starts / Must have by mid-campaign / Nice to have.

| Asset | Format / Specs | Needed By | Status |
|-------|---------------|-----------|--------|

---

### 7. KPIs & Tracking Dashboard

If baseline is unknown, estimate a realistic range for near-launch indie VR game and note it:
Discord: 200-500, Twitter: 200-800, TikTok views: variable, wishlists: 500-2,000.

| Metric | Baseline | Week {weeks//2} Target | Final Target | Track In |
|--------|----------|----------------------|--------------|----------|
| Discord members | | | | Discord |
| Twitter followers | | | | Twitter Analytics |
| TikTok views (total) | | | | TikTok Analytics |
| Wishlist count | | | | Steam/Meta |
| Press coverage pieces | | | | Manual |
| Influencer posts | | | | Manual |

Weekly 15-min check-in: the 3 metrics to review every week (pick what matters most for this goal).

---

### 8. Risk Register

| Risk | Likelihood (H/M/L) | Impact (H/M/L) | Mitigation |
|------|-------------------|----------------|------------|
| Key assets not ready on time | | | |
| Low influencer response rate | | | |
| Solo marketer burnout / capacity | M | H | Batch content; use AI tools; identify 1 week buffer content |
| [Campaign-type-specific risk] | | | |

---

### 9. Weekly Execution Checklist

```
WEEK OF: ___________  (Week X of {weeks})

REVIEW (15 min):
[ ] Check metrics against targets — note what moved
[ ] 1 thing that worked / 1 thing to change
[ ] Reply to community / press / creator messages

THIS WEEK'S CONTENT:
[ ] [Piece 1 — from calendar]
[ ] [Piece 2]
[ ] [Piece 3]

THIS WEEK'S OUTREACH:
[ ] [Who to contact per influencer timeline]

COMMUNITY:
[ ] [Engagement target or community action]

END OF WEEK:
[ ] Metrics logged?
[ ] Carry-forward items noted?
[ ] Next week's content prepped?
```

---

### 10. Solo Marketer Priority Stack

**Do first (highest leverage):**
1. [Activity — explain WHY it's highest leverage for THIS campaign's goal]
2. [Second — brief reason]
3. [Third — brief reason]

**Do if time allows:**
- [Lower priority with reason]

**Skip for this campaign:**
- [Explicitly name the channel or tactic and why it's lower ROI HERE]

**The single metric that matters most**: [One number, and why]
"""


def generate_campaign(
    campaign_type: str,
    timeline: str,
    weeks: int,
    goal: str,
    campaign_name: str,
    client: anthropic.Anthropic,
) -> str:
    """Generate the campaign plan using Claude with streaming."""
    contexts = load_context()

    prompt = build_prompt(campaign_type, timeline, weeks, goal, campaign_name, contexts)

    print(f"\n{'='*60}")
    print(f"  🎪 INWIGO Campaign Architect")
    print(f"{'='*60}")
    print(f"  Name:     {campaign_name}")
    print(f"  Type:     {campaign_type}")
    print(f"  Timeline: {timeline}")
    print(f"  Duration: {weeks} weeks")
    print(f"  Goal:     {goal}")
    print(f"  Model:    claude-opus-4-6 (adaptive thinking)")
    print(f"{'='*60}\n")
    print("Architecting campaign... (2-3 minutes for a full plan)\n")
    print("-" * 60)

    full_response = ""

    with client.messages.stream(
        model="claude-opus-4-6",
        max_tokens=10000,
        thinking={"type": "adaptive"},
        system=(
            "You are a senior marketing strategist who specializes in indie game launches. "
            "You create practical, opinionated campaign plans for solo marketers. "
            "You prioritize ruthlessly and are specific — no generic advice. "
            "Every recommendation should be something one person can actually execute this week. "
            "When you say 'create a TikTok', you mean a specific video with a specific angle. "
            "When you name an influencer tier, you describe the exact type of creator for this campaign."
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
  python agents/campaign_architect.py --type launch --timeline "Q2 2026" --weeks 6 --name "The Carnival Opens" --dry-run
        """,
    )
    parser.add_argument(
        "--type",
        required=True,
        choices=VALID_CAMPAIGN_TYPES,
        help=f"Campaign type. One of: {', '.join(VALID_CAMPAIGN_TYPES)}",
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
        help="Campaign duration in weeks, 1–24 (default: 6)",
    )
    parser.add_argument(
        "--goal",
        default="awareness and wishlists",
        help='Primary campaign goal (default: "awareness and wishlists")',
    )
    parser.add_argument(
        "--name",
        default=None,
        help='Custom campaign name for the document and filename (e.g., "The Carnival Opens")',
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Stream output to stdout only — do not save to file. Useful for testing.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Custom output directory (default: outputs/campaigns/)",
    )
    args = parser.parse_args()

    # Validate
    if args.weeks < 1 or args.weeks > 24:
        print(f"❌ Error: --weeks must be between 1 and 24 (got {args.weeks})")
        sys.exit(1)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("\n❌ Error: ANTHROPIC_API_KEY environment variable is not set.")
        print("   Set it with: export ANTHROPIC_API_KEY='your-key-here'")
        print("   Get a key at: https://console.anthropic.com/")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    # Determine campaign name
    campaign_name = args.name or f"{args.type.replace('-', ' ').title()} — {args.timeline}"

    # Generate
    content = generate_campaign(
        campaign_type=args.type,
        timeline=args.timeline,
        weeks=args.weeks,
        goal=args.goal,
        campaign_name=campaign_name,
        client=client,
    )

    # Dry run — just print, don't save
    if args.dry_run:
        print(f"\n{'='*60}")
        print(f"  ✅ Dry run complete — output not saved")
        print(f"{'='*60}\n")
        return

    # Build filename: timestamp_type_timeline-slug_Xwk.md
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    timeline_slug = slugify(args.timeline, max_len=20)
    filename = f"{timestamp}_{args.type}_{timeline_slug}_{args.weeks}wk.md"

    # Build file with metadata header
    header = f"""---
generated: {datetime.now().isoformat()}
campaign_name: {campaign_name}
campaign_type: {args.type}
timeline: {args.timeline}
weeks: {args.weeks}
goal: {args.goal}
model: claude-opus-4-6
---

# INWIGO Campaign Plan: {campaign_name}
**Timeline**: {args.timeline} | **Duration**: {args.weeks} weeks | **Goal**: {args.goal}

*This plan was generated by the INWIGO Campaign Architect. Review and customize all sections,
especially the influencer/press hit list (requires your own research) and asset checklist
(confirm what you actually have ready).*

---

"""
    full_content = header + content

    # Save
    saved_path = save_campaign(
        full_content,
        filename,
        output_dir=Path(args.output_dir) if args.output_dir else None,
    )

    print(f"\n{'='*60}")
    print(f"  ✅ Campaign plan saved!")
    print(f"{'='*60}")
    print(f"  File: {saved_path.relative_to(PROJECT_ROOT) if saved_path.is_relative_to(PROJECT_ROOT) else saved_path}")
    print(f"\n  Next steps:")
    print(f"  1. Fill in the influencer hit list with real research")
    print(f"  2. Confirm asset availability against the production checklist")
    print(f"  3. Customize the content calendar with your specific topics")
    print(f"  4. Run /social or /outreach to start generating specific content")
    print(f"  5. Fill in game_facts.md if you see [FILL IN] gaps in the plan")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
