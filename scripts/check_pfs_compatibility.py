"""Inspect a host-selected PFS path without executing or changing its files."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

from install_sharepack import manifest

OFFICIAL = 'https://github.com/Lu18835713910/paper-figure-story'


def probe(path):
    if path is None or not path.is_dir():
        return {'status': 'PFS_NOT_FOUND', 'install_independently': OFFICIAL}
    files = manifest(path)
    required = {'SKILL.md', 'VERSION', 'scripts/run_pfs.py'}
    version = (path / 'VERSION').read_text(encoding='utf-8-sig').strip() if 'VERSION' in files else None
    identified = 'SKILL.md' in files and 'name: paper-figure-story' in (path / 'SKILL.md').read_text(
        encoding='utf-8-sig').splitlines()[:10]
    good = required <= files.keys() and identified and version == '1.2.0'
    return {'status': 'SUPPORTED_VERSION' if good else 'PFS_UNSUPPORTED',
            'path': str(path.absolute()), 'version': version,
            'tree_sha256': hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest(),
            'git_revision': 'UNVERIFIED_USE_PFS_INSTALL_RECEIPT',
            'install_independently': OFFICIAL}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--loaded-skill', type=Path)
    result = probe(parser.parse_args().loaded_skill)
    print(json.dumps(result, ensure_ascii=False))
    sys.exit(0 if result['status'] == 'SUPPORTED_VERSION' else 2)
