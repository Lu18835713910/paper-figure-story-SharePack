"""Install, remove, or restore only the explicitly selected SharePack Skill."""
import argparse
import hashlib
import os
from pathlib import Path
import shutil
import stat
import tempfile

NAME = 'paper-figure-story-sharepack'
ROOT_FILES = {'SKILL.md', 'LICENSE', 'LICENSE_STATUS.md', 'NOTICE_THIRD_PARTY.md',
              'NOTICE_PDF_DEPENDENCIES.md', 'INSTALL.md', 'VERSION'}
SCRIPTS = {'install_sharepack.py', 'render_reviewed.py', 'pfs_logic_projection.py',
           'check_pfs_compatibility.py', 'draft_ab_view_spec.py', 'verify_real_pfs_bridge.py'}


def check_path(path):
    for part in (path, *path.parents):
        if part.is_symlink() or (part.exists() and
                getattr(part.lstat(), 'st_file_attributes', 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT):
            raise ValueError(f'Linked path is unsupported: {part}')


def manifest(path):
    check_path(path)
    rows = {}
    for directory, folders, files in os.walk(path):
        for item in folders + files:
            entry = Path(directory) / item
            check_path(entry)
            if entry.is_file():
                rows[entry.relative_to(path).as_posix()] = hashlib.sha256(entry.read_bytes()).hexdigest()
    return rows


def recognized(path):
    check_path(path / 'SKILL.md')
    return 'name: ' + NAME in (path / 'SKILL.md').read_text(encoding='utf-8-sig').splitlines()[:10]


def switch(root, action, source=None, backup=None):
    root = root.absolute()
    if root.name != 'skills' or not root.is_dir():
        raise ValueError('Supply the existing skills directory of one host')
    check_path(root)
    target = root / NAME
    check_path(target)
    if target.exists() and not recognized(target):
        raise ValueError('Target is not an identified SharePack Skill')
    vault = root.parent / 'sharepack-skill-backups'
    check_path(vault)
    if action == 'rollback':
        if not backup or Path(backup).name != backup or not backup.startswith('sharepack-'):
            raise ValueError('Supply a SharePack backup ID for this host')
        source = vault / backup
    if action != 'uninstall':
        source = source.absolute()
        check_path(source)
        if source == target or source.is_relative_to(target) or not recognized(source):
            raise ValueError('Select an extracted SharePack bundle or backup')
        allowed = ROOT_FILES | {'references/SKILL_BRANDING_ADDENDUM.md'}
        allowed |= {f'scripts/{name}' for name in SCRIPTS}
        files = {}
        for key in sorted(allowed):
            path = source / key
            check_path(path)
            if path.is_file():
                files[key] = hashlib.sha256(path.read_bytes()).hexdigest()
        if target.exists() and manifest(target) == files:
            return 'UNCHANGED'
    elif not target.exists():
        return 'UNCHANGED'
    vault.mkdir(exist_ok=True)
    transaction = Path(tempfile.mkdtemp(prefix='sharepack-', dir=vault))
    stage = transaction / 'stage'
    old = transaction / 'previous'
    if action != 'uninstall':
        stage.mkdir()
        for key in files:
            dest = stage / key
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source / key, dest)
        if manifest(stage) != files:
            raise ValueError('Staged SharePack bytes differ')
    if target.exists():
        target.rename(old)
    try:
        if action != 'uninstall':
            stage.rename(target)
    except OSError:
        if old.exists():
            old.rename(target)
        raise
    if old.exists():
        saved = vault / (transaction.name + '-previous')
        old.rename(saved)
        return saved.name
    return 'INSTALLED'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=('install', 'uninstall', 'rollback'))
    p.add_argument('--skills-dir', required=True, type=Path)
    p.add_argument('--source', type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument('--backup')
    a = p.parse_args()
    try:
        print(switch(a.skills_dir, a.action, a.source, a.backup))
    except (ValueError, OSError) as exc:
        p.exit(2, f'{exc}\n')


if __name__ == '__main__':
    main()
