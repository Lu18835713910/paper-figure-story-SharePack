import importlib.util
from pathlib import Path
import unittest
import tempfile
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('installer', Path(__file__).parents[1] / 'scripts/install_sharepack.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class Isolation(unittest.TestCase):
    def test_install_upgrade_rollback_uninstall_and_failed_replace(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / 'bundle'
            source.mkdir()
            md = source / 'SKILL.md'
            md.write_text('name: paper-figure-story-sharepack\nfirst')
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
