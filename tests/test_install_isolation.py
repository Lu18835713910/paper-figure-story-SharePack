import importlib.util
from pathlib import Path
import unittest
import tempfile
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('installer', Path(__file__).parents[1] / 'scripts/install_sharepack.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


def create_complete_bundle(source):
    """Construct the complete independently installable Skill bundle."""
    for key in sorted(installer.REQUIRED_FILES):
        path = source / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('name: paper-figure-story-sharepack\\nfirst' if key == 'SKILL.md'
                        else ('1.0.0' if key == 'VERSION' else key))
    return source / 'SKILL.md'


class Isolation(unittest.TestCase):
    def test_install_upgrade_rollback_uninstall_and_failed_replace(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / 'bundle'
            source.mkdir()
            md = create_complete_bundle(source)
            (source / 'paper-figure-story').mkdir()
            (source / 'paper-figure-story/VERSION').write_text('must not ship')
            codex, buddy = [root / host / 'skills' for host in ('codex', 'workbuddy')]
            for path in codex, buddy:
                path.mkdir(parents=True)
            self.assertEqual(installer.switch(codex, 'install', source), 'INSTALLED')
            self.assertFalse((codex / 'paper-figure-story').exists())
            states = {}
            for path, revision in ((codex, '89e583d'), (buddy, '69d7618')):
                pfs = path / 'paper-figure-story'
                pfs.mkdir()
                (pfs / 'VERSION').write_text('1.2.0')
                (pfs / 'revision').write_text(revision)
                states[pfs] = installer.manifest(pfs)
            self.assertEqual(installer.switch(codex, 'install', source), 'UNCHANGED')
            md.write_text('name: paper-figure-story-sharepack\nsecond')
            backup = installer.switch(codex, 'install', source)
            self.assertFalse((buddy / installer.NAME).exists())
            self.assertFalse((codex / installer.NAME / 'paper-figure-story').exists())
            installer.switch(codex, 'rollback', backup=backup)
            target = codex / installer.NAME
            self.assertIn('first', (target / 'SKILL.md').read_text())
            rename = Path.rename

            def fail_stage(path, dest):
                if path.name == 'stage':
                    raise OSError('injected failure')
                return rename(path, dest)

            with patch.object(Path, 'rename', fail_stage), self.assertRaises(OSError):
                installer.switch(codex, 'install', source)
            self.assertIn('first', (target / 'SKILL.md').read_text())
            installer.switch(codex, 'uninstall')
            self.assertFalse(target.exists())
            installer.switch(buddy, 'install', source)
            for path, state in states.items():
                self.assertEqual(installer.manifest(path), state)

    def test_incomplete_bundle_rejected_before_active_replacement(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / 'bundle'
            source.mkdir()
            create_complete_bundle(source)
            skills = root / 'skills'
            skills.mkdir()
            pfs = skills / 'paper-figure-story'
            pfs.mkdir()
            (pfs / 'VERSION').write_text('1.2.0')
            original_pfs = installer.manifest(pfs)
            installer.switch(skills, 'install', source)
            original_sharepack = installer.manifest(skills / installer.NAME)
            for key in sorted(installer.REQUIRED_FILES - {'SKILL.md'}):
                path = source / key
                payload = path.read_bytes()
                path.unlink()
                with self.subTest(missing=key), self.assertRaisesRegex(ValueError, 'Incomplete SharePack'):
                    installer.switch(skills, 'install', source)
                self.assertEqual(installer.manifest(skills / installer.NAME), original_sharepack)
                self.assertEqual(installer.manifest(pfs), original_pfs)
                path.write_bytes(payload)

    def test_legacy_backup_rollback_supported(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / 'bundle'
            source.mkdir()
            create_complete_bundle(source)
            skills = root / 'skills'
            skills.mkdir()
            legacy = root / 'sharepack-skill-backups' / 'sharepack-legacy-previous'
            legacy.mkdir(parents=True)
            (legacy / 'SKILL.md').write_text('name: paper-figure-story-sharepack\\nlegacy')
            (legacy / 'VERSION').write_text('0.9.0')
            installer.switch(skills, 'install', source)
            installer.switch(skills, 'rollback', backup=legacy.name)
            self.assertEqual((skills / installer.NAME / 'VERSION').read_text(), '0.9.0')
            self.assertFalse((skills / installer.NAME / 'scripts/install_sharepack.py').exists())

    def test_empty_version_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / 'bundle'
            source.mkdir()
            create_complete_bundle(source)
            (source / 'VERSION').write_text('')
            skills = root / 'skills'
            skills.mkdir()
            with self.assertRaisesRegex(ValueError, 'VERSION file is empty'):
                installer.switch(skills, 'install', source)
            self.assertFalse((skills / installer.NAME).exists())

