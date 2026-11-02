"""Behavior checks for the Go model-change gate and stacked PR triggers."""

from pathlib import Path
import subprocess
import tempfile
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]


class StabilizationTests(unittest.TestCase):
    def test_title_guard_covers_stack(self):
        data = yaml.safe_load((ROOT / '.github/workflows/pr-title.yml').read_text())
        trigger = data.get('on', data.get(True))['pull_request']
        self.assertNotIn('branches', trigger)
        self.assertEqual(data['jobs']['pr-title-guard']['if'],
                         "github.event.pull_request.base.ref != 'main'")

    def test_model_change_requires_new_record(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)

            def git(*args):
                return subprocess.run(['git', '-c', 'core.hooksPath=/dev/null', *args],
                                      cwd=root, check=True, capture_output=True, text=True)

            git('init')
            git('config', 'user.name', 'Fixture')
            git('config', 'user.email', 'fixture@example.invalid')
            (root / 'architecture').mkdir()
            model = root / 'architecture/model.yaml'
            model.write_text('rules: [strict]\n')
            (root / 'Makefile').write_text((ROOT / 'Makefile').read_text())
            git('add', '.')
            git('commit', '-m', 'base')
            base = git('rev-parse', 'HEAD').stdout.strip()

            def gate():
                return subprocess.run(['make', 'go-arch-change', f'BASE={base}'],
                                      cwd=root, capture_output=True, text=True)

            self.assertEqual(gate().returncode, 0)
            model.write_text('rules: [weakened]\n')
            git('add', '.')
            git('commit', '-m', 'change without design')
            result = gate()
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('design-change', result.stderr)
            records = root / 'docs/development/designs'
            records.mkdir(parents=True)
            (records / '0001-change.md').write_text('Design\n')
            git('add', '.')
            git('commit', '-m', 'add design')
            self.assertEqual(gate().returncode, 0)
