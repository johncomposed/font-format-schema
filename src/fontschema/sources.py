from __future__ import annotations

import subprocess
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .common import dump_json, repo_root


@dataclass(frozen=True)
class Upstream:
    name: str
    url: str
    ref: str
    prefix: str
    role: str = ""


def load_upstreams() -> list[Upstream]:
    manifest = repo_root() / "sources" / "upstreams.toml"
    raw = tomllib.loads(manifest.read_text(encoding="utf-8"))
    return [Upstream(**item) for item in raw.get("source", [])]


def _run(args: list[str], cwd: Path | None = None) -> None:
    subprocess.run(args, cwd=cwd, check=True)


def _capture(args: list[str], cwd: Path | None = None) -> str:
    return subprocess.check_output(args, cwd=cwd, text=True).strip()


def _resolve_ref(dest: Path, ref: str) -> str:
    candidates = [f"refs/tags/{ref}", f"origin/{ref}", ref]
    for candidate in candidates:
        try:
            _capture(["git", "rev-parse", "--verify", candidate], cwd=dest)
            return candidate
        except subprocess.CalledProcessError:
            pass
    raise SystemExit(f"cannot resolve git ref {ref!r} in {dest}")


def sync_cache(upstreams: Iterable[Upstream] | None = None) -> None:
    root = repo_root()
    cache = root / ".cache" / "upstreams"
    cache.mkdir(parents=True, exist_ok=True)
    lock_rows = []
    for src in upstreams or load_upstreams():
        dest = cache / src.name
        if not dest.exists():
            _run(["git", "clone", "--filter=blob:none", src.url, str(dest)])
        _run(["git", "fetch", "--tags", "origin"], cwd=dest)
        target = _resolve_ref(dest, src.ref)
        _run(["git", "checkout", "--detach", target], cwd=dest)
        commit = _capture(["git", "rev-parse", "HEAD"], cwd=dest)
        lock_rows.append({"name": src.name, "url": src.url, "declaredRef": src.ref, "resolvedCommit": commit})
    dump_json({"sources": lock_rows}, root / ".cache" / "upstreams-lock.json")


def source_path(name: str) -> Path | None:
    root = repo_root()
    for src in load_upstreams():
        if src.name != name:
            continue
        vendored = root / src.prefix
        if vendored.exists():
            return vendored
        cached = root / ".cache" / "upstreams" / name
        if cached.exists():
            return cached
    return None


def status() -> list[dict[str, str | bool | None]]:
    root = repo_root()
    rows = []
    for src in load_upstreams():
        vendored = root / src.prefix
        cached = root / ".cache" / "upstreams" / src.name
        active = vendored if vendored.exists() else cached if cached.exists() else None
        commit = None
        if active is not None and (active / ".git").exists():
            try:
                commit = _capture(["git", "rev-parse", "HEAD"], cwd=active)
            except subprocess.CalledProcessError:
                pass
        rows.append({
            "name": src.name,
            "ref": src.ref,
            "vendored": vendored.exists(),
            "cached": cached.exists(),
            "path": str(active or ""),
            "commit": commit,
        })
    return rows


def subtree_init() -> None:
    root = repo_root()
    for src in load_upstreams():
        prefix = root / src.prefix
        if prefix.exists():
            print(f"skip {src.name}: {src.prefix} already exists")
            continue
        _run([
            "git", "subtree", "add", "--squash",
            f"--prefix={src.prefix}", src.url, src.ref,
        ], cwd=root)


def subtree_update() -> None:
    root = repo_root()
    for src in load_upstreams():
        prefix = root / src.prefix
        if not prefix.exists():
            raise SystemExit(f"missing {src.prefix}; run subtree-init first")
        _run([
            "git", "subtree", "pull", "--squash",
            f"--prefix={src.prefix}", src.url, src.ref,
        ], cwd=root)
