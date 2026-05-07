"""Install production-grade skills + protocols into QwenPaw agent workspaces.

The installer prefers **bundled** content if this plugin's ``skills/`` and
``protocols/`` dirs are populated (run ``python -m
production_grade.port_from_upstream`` once to populate). If the bundled dirs
are missing or empty, it falls back to **live-porting** from your local copy
of ``nagisanzenin/claude-code-production-grade-plugin`` (MIT) at install time.

Three things happen per workspace:

1. Adapted ``SKILL.md`` files written under ``<workspace>/skills/<name>/``.
2. Verbatim protocol files written under
   ``<workspace>/production-grade-protocols/``.
3. Each ported skill is registered/enabled in
   ``<workspace>/skill.json`` (the per-agent manifest QwenPaw reads to
   populate its Skills tab and to route ``/<name>`` invocations).

Without step 3 the skills exist on disk but don't show up in the QwenPaw
console UI — that's the v0.1.1 fix vs v0.1.0.
"""
from __future__ import annotations

import json
import logging
import os
import re
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

from production_grade.port_logic import adapt_skill

log = logging.getLogger("production-grade.installer")

PG_VERSION = "0.1.1"
SKILL_NAMES = [
    "production-grade", "polymath", "product-manager", "solution-architect",
    "software-engineer", "frontend-engineer", "qa-engineer", "security-engineer",
    "code-reviewer", "devops", "sre", "technical-writer", "data-scientist",
    "skill-maker",
]

# ─── Public API ─────────────────────────────────────────────────────────────


def install_skills_to_all_workspaces(plugin_root: Path) -> int:
    bundle = _find_bundle(plugin_root)
    if bundle is not None:
        skills_src, protocols_src = bundle
        bundled = True
        print(
            f"[production-grade] using bundled skills+protocols from {plugin_root}",
            flush=True,
        )
    else:
        upstream = _resolve_upstream(plugin_root)
        if upstream is None:
            raise FileNotFoundError(
                "No bundled skills/ in this plugin and no upstream "
                "production-grade plugin found. Either run "
                "`python -m production_grade.port_from_upstream` to "
                "populate skills/ and protocols/, or set "
                "CLAUDE_PRODUCTION_GRADE_UPSTREAM=/abs/path."
            )
        log.info("upstream resolved to %s", upstream)
        skills_src = upstream / "skills"
        protocols_src = skills_src / "_shared" / "protocols"
        bundled = False
        print(
            f"[production-grade] live-porting from upstream at {upstream}",
            flush=True,
        )

    if not skills_src.is_dir():
        raise FileNotFoundError(f"skills source dir missing: {skills_src}")

    ws_root = _resolve_workspaces_root()
    if not ws_root.exists():
        log.warning("no QwenPaw workspaces found at %s", ws_root)
        print(
            f"[production-grade] no workspaces at {ws_root}; "
            f"run `qwenpaw init --defaults` first",
            flush=True,
        )
        return 0

    n = 0
    for agent_dir in sorted(ws_root.iterdir()):
        if not agent_dir.is_dir():
            continue
        _install_into_workspace(
            workspace=agent_dir,
            skills_src=skills_src,
            protocols_src=protocols_src,
            bundled=bundled,
        )
        n += 1
    return n


# ─── Workspace install ──────────────────────────────────────────────────────


def _install_into_workspace(
    *,
    workspace: Path,
    skills_src: Path,
    protocols_src: Path,
    bundled: bool,
) -> None:
    dst_skills = workspace / "skills"
    dst_protocols = workspace / "production-grade-protocols"
    dst_skills.mkdir(exist_ok=True)
    dst_protocols.mkdir(exist_ok=True)

    if protocols_src.is_dir():
        for src in protocols_src.iterdir():
            if src.is_file() and src.suffix == ".md":
                shutil.copy2(src, dst_protocols / src.name)

    installed_metadata: dict[str, dict] = {}
    for src_dir in skills_src.iterdir():
        if not src_dir.is_dir() or src_dir.name.startswith("_"):
            continue
        src_md = src_dir / "SKILL.md"
        if not src_md.is_file():
            continue
        dst_dir = dst_skills / src_dir.name
        dst_dir.mkdir(exist_ok=True)
        text = src_md.read_text(encoding="utf-8")
        if bundled:
            text = text.replace("${PG_PROTOCOLS}", str(dst_protocols))
        else:
            text = adapt_skill(text, protocols_dir=dst_protocols)
        (dst_dir / "SKILL.md").write_text(text, encoding="utf-8")
        installed_metadata[src_dir.name] = _extract_skill_metadata(text)

    _update_skill_manifest(workspace, installed_metadata)

    log.info("workspace %s: installed %d skills", workspace.name, len(installed_metadata))
    print(
        f"[production-grade]   ✓ {workspace.name}: {len(installed_metadata)} skills",
        flush=True,
    )


# ─── Skill manifest registration ────────────────────────────────────────────

_FM_FENCE = re.compile(r"^---\s*$", re.MULTILINE)
_FM_NAME = re.compile(r"^name:\s*(.+?)\s*$", re.MULTILINE)
_FM_DESCRIPTION = re.compile(r"^description:\s*(.+?)(?=\n[A-Za-z][A-Za-z0-9_-]*:|\n---|\Z)", re.DOTALL | re.MULTILINE)


def _extract_skill_metadata(skill_md_text: str) -> dict:
    """Pull (name, description) from a SKILL.md body's YAML frontmatter."""
    fm_match = list(_FM_FENCE.finditer(skill_md_text))
    if len(fm_match) < 2:
        return {"name": "", "description": ""}
    fm = skill_md_text[fm_match[0].end():fm_match[1].start()]
    name = (_FM_NAME.search(fm).group(1).strip() if _FM_NAME.search(fm) else "")
    desc_m = _FM_DESCRIPTION.search(fm)
    description = ""
    if desc_m:
        raw = desc_m.group(1).strip()
        # YAML folded scalar (>) collapses newlines into spaces; treat like that.
        if raw.startswith(">"):
            raw = raw[1:].strip()
        description = re.sub(r"\s+", " ", raw)
    return {"name": name, "description": description}


def _update_skill_manifest(workspace: Path, installed: dict[str, dict]) -> None:
    """Add/update ``<workspace>/skill.json`` so each ported skill is enabled
    and visible in the QwenPaw Skills tab.

    Preserves entries for skills not in this plugin (built-ins, other plugins,
    user-customized skills).
    """
    manifest_path = workspace / "skill.json"
    now_ms = int(time.time() * 1000)
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            log.warning("skill.json malformed; rewriting from scratch")
            manifest = {}
    else:
        manifest = {}

    manifest.setdefault("schema_version", "workspace-skill-manifest.v1")
    manifest["version"] = now_ms
    skills = manifest.setdefault("skills", {})

    for skill_name, meta in installed.items():
        existing = skills.get(skill_name, {})
        # Preserve user-set channels/config if already present.
        skill_entry = {
            "enabled": existing.get("enabled", True),
            "channels": existing.get("channels", ["all"]),
            "source": "customized",
            "metadata": {
                "name": meta.get("name", skill_name),
                "description": meta.get("description", ""),
                "version_text": PG_VERSION,
                "commit_text": "",
                "source": "customized",
                "protected": False,
                "requirements": {"require_bins": [], "require_envs": []},
                "updated_at": now_iso,
            },
            "requirements": {"require_bins": [], "require_envs": []},
            "updated_at": now_iso,
            "config": existing.get("config", {}),
        }
        skills[skill_name] = skill_entry

    tmp = manifest_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    tmp.replace(manifest_path)


# ─── Bundle / upstream resolution ──────────────────────────────────────────


def _find_bundle(plugin_root: Path) -> tuple[Path, Path] | None:
    skills = plugin_root / "skills"
    protocols = plugin_root / "protocols"
    has_skills = skills.is_dir() and any(
        (p / "SKILL.md").is_file()
        for p in skills.iterdir() if p.is_dir() and not p.name.startswith("_")
    )
    if has_skills:
        return skills, protocols if protocols.is_dir() else skills / "_protocols_missing"
    return None


def _resolve_upstream(plugin_root: Path) -> Path | None:
    candidates: list[Path] = []
    env = os.environ.get("CLAUDE_PRODUCTION_GRADE_UPSTREAM")
    if env:
        candidates.append(Path(env).expanduser())
    candidates.extend([
        Path.home() / "Documents" / "Github" / "claude-code-production-grade-plugin",
        plugin_root.parent / "claude-code-production-grade-plugin",
    ])
    cache = (
        Path.home() / ".claude" / "plugins" / "cache"
        / "nagisanzenin" / "production-grade"
    )
    if cache.is_dir():
        for v in sorted(
            (p for p in cache.iterdir() if p.is_dir()),
            key=lambda p: p.name,
            reverse=True,
        ):
            candidates.append(v)
    for c in candidates:
        if c.is_dir() and (c / "skills").is_dir():
            return c.resolve()
    return None


def _resolve_workspaces_root() -> Path:
    try:
        from qwenpaw.constant import WORKING_DIR  # type: ignore[import]

        return Path(WORKING_DIR).expanduser() / "workspaces"
    except Exception:  # noqa: BLE001
        return Path.home() / ".qwenpaw" / "workspaces"
