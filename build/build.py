#!/usr/bin/env python3
"""Regenerate every per-target skill copy from a single source of truth.

WHY: the toolkit is shipped four ways (Claude Code plugin, Codex open-repo, and two
drag-and-drop bundles), each needing a SKILL.md with a different script path, and the two
drag-and-drop bundles need their own copy of the Python scripts. Hand-maintaining those
copies invites drift. Edit the sources, run this once, and every copy is regenerated.

SOURCES OF TRUTH (edit these):
  scripts/*.py                 -- the engine
  build/SKILL.template.md      -- the skill methodology ({{SCRIPTS}} = path to the scripts)

GENERATED (do not edit by hand):
  skills/youtube-topic-research/SKILL.md                          (Claude Code plugin)
  .codex/skills/youtube-topic-research/SKILL.md                   (Codex, open-repo)
  install/claude/youtube-topic-research/{SKILL.md, scripts/*}     (Claude drag-and-drop)
  install/codex/youtube-topic-research/{SKILL.md, scripts/*}      (Codex drag-and-drop)

USAGE:
  python build/build.py            regenerate all copies
  python build/build.py --check    verify everything is in sync; exit 1 if not (writes nothing)
"""
import filecmp
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "build" / "SKILL.template.md"
SCRIPTS_DIR = ROOT / "scripts"
SCRIPT_FILES = ("trends_serpapi.py", "youtube_competition.py", "_env.py")

# SKILL.md output path -> the {{SCRIPTS}} value for that install location.
SKILL_TARGETS = {
    "skills/youtube-topic-research/SKILL.md": "${CLAUDE_PLUGIN_ROOT}/scripts",
    ".codex/skills/youtube-topic-research/SKILL.md": "scripts",
    "install/claude/youtube-topic-research/SKILL.md": "${CLAUDE_SKILL_DIR}/scripts",
    "install/codex/youtube-topic-research/SKILL.md":
        "~/.codex/skills/youtube-topic-research/scripts",
}

# Drag-and-drop bundles that must carry their own copy of the scripts (self-contained).
BUNDLE_SCRIPT_DIRS = (
    "install/claude/youtube-topic-research/scripts",
    "install/codex/youtube-topic-research/scripts",
)


def _read(path):
    # Universal-newline read: CRLF or LF on disk both compare as \n.
    return path.read_text(encoding="utf-8")


def _write(path, text):
    # Force LF so regeneration never churns line endings.
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def main(argv):
    check = "--check" in argv
    template = _read(TEMPLATE)
    drift, wrote = [], []

    # 1. SKILL.md files (one template, per-target path substitution).
    for rel, scripts_value in SKILL_TARGETS.items():
        target = ROOT / rel
        rendered = template.replace("{{SCRIPTS}}", scripts_value)
        current = _read(target) if target.is_file() else None
        if current == rendered:
            continue
        if check:
            drift.append(rel)
        else:
            _write(target, rendered)
            wrote.append(rel)

    # 2. Script copies inside the self-contained drag-and-drop bundles.
    for rel_dir in BUNDLE_SCRIPT_DIRS:
        for fn in SCRIPT_FILES:
            src, dst = SCRIPTS_DIR / fn, ROOT / rel_dir / fn
            in_sync = dst.is_file() and filecmp.cmp(src, dst, shallow=False)
            if in_sync:
                continue
            if check:
                drift.append(f"{rel_dir}/{fn}")
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                wrote.append(f"{rel_dir}/{fn}")

    if check:
        if drift:
            print("OUT OF SYNC (run `python build/build.py` to fix):")
            for d in drift:
                print("  -", d)
            return 1
        print("In sync: all generated copies match the sources.")
        return 0

    if wrote:
        print("Regenerated:")
        for w in wrote:
            print("  -", w)
    else:
        print("Already in sync — nothing to regenerate.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
