#!/usr/bin/env python3
"""
INWIGO Content Batch Agent
--------------------------
Generates a full week of content across all platforms in one shot.

Usage:
    python agents/content_batch_agent.py --theme "Halloween countdown" --week "Week of Oct 14"
    python agents/content_batch_agent.py --theme "Launch week" --week "Oct 28-Nov 3" --focus social
    python agents/content_batch_agent.py --theme "Character reveal" --dry-run
    python agents/content_batch_agent.py --help

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


# Project root (one level up from this agents/ directory)
PROJECT_ROOT = Path(__file__).parent.parent


def load_context(allow_missing: bool = False) -> dict[str, str]:
    """Load all context files. Warns if any are missing or have unfilled placeholders."""
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
                print(f"  ⚠️  {fname}: {fill_count} [FILL IN] placeholder(s) — "
                      f"generated content will note these gaps")
        else:
            missing.append(fname)
            print(f"  ❌ {fname} not found at {fpath}")
            contexts[fname] = f"[{fname} not found — please create context/{fname}]"

    if missing and not allow_missing:
        print(f"\n  ⛔ Cannot continue: {len(missing)} context file(s) missing.")
        print(f"     Create them in context/ or use --allow-missing-context to proceed anyway.")
        sys.exit(1)

    return contexts


def save_output(content: str, subdirectory: str, filename: str) -> Path:
    """Save generated content to the outputs directory."""
    output_dir = PROJECT_ROOT / "outputs" / subdirectory
    output_dir.mkdir(parents=True, exist_ok=True)
    fpath = output_dir / filename
    fpath.write_text(content, encoding="utf-8")
    return fpath


def truncate_at_word_boundary(text: str, max_len: int) -> str:
    """Truncate a string at a word boundary, not mid-word."""
    if len(text) <= max_len:
        return text
    words = text.split("_")
    result = []
    current_len = 0
    for word in words:
        addition = len(word) + (1 if result else 0)  # account for underscore separator
        if current_len + addition > max_len:
            break
        result.append(word)
        current_len += addition
    return "_".join(result)


def build_prompt(theme: str, week: str, focus: str, contexts: dict[str, str]) -> str:
    """Build the generation prompt for the content batch."""

    focus_instruction = {
        "all": "Generate ALL content types listed below.",
        "social": "Focus on SOCIAL MEDIA content only (Twitter/X, Instagram, TikTok).",
        "video": "Focus on VIDEO content only (TikTok scripts and YouTube Short scripts).",
        "community": "Focus on COMMUNITY content only (Discord announcement and Reddit post).",
        "discord": "Focus on DISCORD content only (Discord weekly update).",
        "reddit": "Focus on REDDIT content only (one Reddit post).",
        "blog": "Focus on BLOG/LONGFORM content only (blog post opening + outline).",
    }.get(focus, "Generate ALL content types listed below.")

    return f"""You are the content team for INWIGO. Generate a complete week of publication-ready content.

## Brand Context

### Brand Kit
{contexts['brand_kit.md']}

### Game Facts
{contexts['game_facts.md']}

### Audience Personas
{contexts['audience_personas.md']}

---

## Task

Generate a full content batch for **{week}** built around the theme: **"{theme}"**

{focus_instruction}

For any content referencing specific game details that are marked [FILL IN], write the best
placeholder you can and mark it clearly with **[NEEDS REVIEW: reason]** so the marketer knows
what to customize before publishing.

---

## Content to Generate

### 📱 TWITTER / X POSTS (5 posts)

For each post:
- **Post [1-5]**
  - Text: [max 280 chars, no hashtags in body]
  - Hashtags: [3-5 tags as separate line]
  - Visual: [screenshot/clip/GIF direction]
  - Best day: [Mon-Fri recommendation]
  - Targets: [Alex / Morgan / Jordan — which persona does this serve]

---

### 📸 INSTAGRAM CAPTIONS (3 captions)

For each caption:
- **Caption [1-3]** — [angle/topic]
  - Hook (visible before "more"): [First line]
  - Full caption: [2-4 paragraphs with natural line breaks]
  - CTA: [Specific action]
  - Caption hashtags: [5-10 targeted tags — best for algorithm]
  - Extended hashtag block: [20-25 tags for first comment]
  - Visual direction: [What type of image/video works best]
  - Targets: [Alex / Morgan / Jordan]

---

### 🎵 TIKTOK SCRIPTS (2 scripts)

For each:
- **Script [1-2]** — [topic/angle]
  - Duration: [target seconds]
  - Hook (0-2s): [Text overlay or opening action — must work without sound]
  - Structure: [time-stamped notes on visuals and text overlays]
  - VO/caption: [Voiceover only if narrated content — omit for gameplay/reaction]
  - Music direction: [Energy/mood]
  - Hashtags: [TikTok-optimized]
  - Targets: [Alex / Morgan / Jordan]

---

### 💬 DISCORD WEEKLY UPDATE (1 post)

Full Discord-formatted announcement using Discord markdown (##, **, *, >).
Include emojis appropriate to INWIGO (🎃, 👻, 🎡, 🎪, 🎠). 2-5 emojis per post.
Structure: Header → hook → sections → CTA.

---

### 🌐 REDDIT POST (1 post)

For r/VRGaming or the most relevant subreddit for this theme.
- Title: [subreddit-appropriate]
- Body: dev-owned, honest, value-first, ends with a question
- Links: clearly labeled, not buried
- Remember: acknowledge you're the developer in the first line

---

### 📝 BLOG POST OPENING + OUTLINE (1 piece)

- **Title**: [Engaging, SEO-conscious — include "INWIGO VR" + topic keyword]
- **Meta description**: [150-160 chars — include primary keyword]
- **Opening paragraph**: [Write the actual first 2-3 sentences of the post — not a description of what they'll be, but the real thing. Hook the reader.]
- **Section 1**: [Title + 3 specific key points to cover — not just "cover X" but real points]
- **Section 2**: [Title + 3 specific key points]
- **Section 3**: [Title + 3 specific key points]
- **Section 4**: [Title + 3 specific key points]
- **Section 5** (optional): [Title + 3 specific key points]
- **Conclusion approach**: [How to close + CTA]
- **Estimated read time**: [X min]

---

## Quality Reminders

- Every piece should feel like it was written by a real person who loves this game
- Playfully spooky, community-first, chaotically charming — always
- No corporate PR language
- If in doubt, be more human and less polished
- Each post targets a specific persona — the best INWIGO content feels like it was made for that person
"""


def generate_content_batch(
    theme: str,
    week: str,
    focus: str,
    client: anthropic.Anthropic,
    allow_missing: bool = False,
) -> str:
    """Generate the content batch using Claude with streaming."""
    contexts = load_context(allow_missing=allow_missing)

    prompt = build_prompt(theme, week, focus, contexts)

    print(f"\n{'='*60}")
    print(f"  🎠 INWIGO Content Batch Generator")
    print(f"{'='*60}")
    print(f"  Week:   {week}")
    print(f"  Theme:  {theme}")
    print(f"  Focus:  {focus}")
    print(f"  Model:  claude-opus-4-6 (adaptive thinking)")
    print(f"{'='*60}\n")
    print("Generating content... (60-90 seconds)\n")
    print("-" * 60)

    full_response = ""

    with client.messages.stream(
        model="claude-opus-4-6",
        max_tokens=8000,
        thinking={"type": "adaptive"},
        system=(
            "You are the sole content creator for INWIGO, an indie VR horror-survival game "
            "set in a Halloween carnival — like Lethal Company in VR, with a Don't Starve art style. "
            "You write with genuine enthusiasm and the INWIGO voice: playfully spooky, "
            "community-first, chaotically charming, authentically indie. "
            "Never write corporate copy. Never be generic. Every line should feel like it was "
            "written by someone who has played this game and loves it. "
            "Content that makes someone want to tag a friend is the standard."
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
        description="Generate a full week of INWIGO content across all platforms.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python agents/content_batch_agent.py --theme "Halloween countdown" --week "Week of Oct 14"
  python agents/content_batch_agent.py --theme "Launch week" --week "Oct 28" --focus social
  python agents/content_batch_agent.py --theme "New carnival area reveal" --focus video
  python agents/content_batch_agent.py --theme "Test prompt" --dry-run
        """,
    )
    parser.add_argument(
        "--theme",
        required=True,
        help='Weekly content theme (e.g., "Halloween countdown", "Launch week")',
    )
    parser.add_argument(
        "--week",
        default=datetime.now().strftime("Week of %B %d, %Y"),
        help='Week identifier (e.g., "Week of Oct 14"). Defaults to current week.',
    )
    parser.add_argument(
        "--focus",
        default="all",
        choices=["all", "social", "video", "community", "discord", "reddit", "blog"],
        help="Which content types to generate (default: all). "
             "'community' generates both Discord and Reddit.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Stream output to stdout only — do not save to file. Useful for testing.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Custom output directory (default: outputs/batches/)",
    )
    parser.add_argument(
        "--allow-missing-context",
        action="store_true",
        help="Continue even if context files are missing (output quality will be reduced).",
    )
    args = parser.parse_args()

    # Validate API key
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("\n❌ Error: ANTHROPIC_API_KEY environment variable is not set.")
        print("   Set it with: export ANTHROPIC_API_KEY='your-key-here'")
        print("   Get a key at: https://console.anthropic.com/")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    # Generate content
    content = generate_content_batch(
        theme=args.theme,
        week=args.week,
        focus=args.focus,
        client=client,
        allow_missing=args.allow_missing_context,
    )

    # Dry run — just print, don't save
    if args.dry_run:
        print(f"\n{'='*60}")
        print(f"  ✅ Dry run complete — output not saved")
        print(f"{'='*60}\n")
        return

    # Build output filename with word-boundary truncation
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    safe_theme = truncate_at_word_boundary(
        args.theme.replace(" ", "_").replace("/", "-").replace(":", "").replace('"', ""),
        max_len=40,
    )
    filename = f"{timestamp}_{safe_theme}.md"

    # Add metadata header
    header = f"""---
generated: {datetime.now().isoformat()}
week: {args.week}
theme: {args.theme}
focus: {args.focus}
model: claude-opus-4-6
---

# INWIGO Content Batch: {args.week}
**Theme**: {args.theme} | **Focus**: {args.focus}

*Review all [NEEDS REVIEW] markers before publishing. Update game_facts.md with any confirmed details.*

---

"""
    full_content = header + content

    # Determine output directory
    if args.output_dir:
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        saved_path = output_dir / filename
        saved_path.write_text(full_content, encoding="utf-8")
    else:
        saved_path = save_output(full_content, "batches", filename)

    print(f"\n{'='*60}")
    print(f"  ✅ Content batch saved!")
    print(f"{'='*60}")
    print(f"  File: {saved_path.relative_to(PROJECT_ROOT) if saved_path.is_relative_to(PROJECT_ROOT) else saved_path}")
    print(f"\n  Next steps:")
    print(f"  1. Review [NEEDS REVIEW] markers and customize")
    print(f"  2. Fill in any [FILL IN] fields in context/game_facts.md")
    print(f"  3. Schedule posts using your preferred scheduling tool")
    print(f"  4. Move used posts to outputs/social/ after publishing")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
