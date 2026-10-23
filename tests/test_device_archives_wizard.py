"""Guided decisions exercise real verified snapshots, without a live terminal."""
import unittest
from unittest.mock import patch

import test_device_archives as fixtures
from device_archives.core import ArchiveError
from device_archives.wizard import setup, visible


class UI:
    def __init__(self, choices, confirmations=()):
        self.choices = iter(choices)
        self.confirmations = iter(confirmations)
        self.pages, self.rows, self.prompts = [], [], []

    def choose(self, title, options):
        choice = next(self.choices)
        assert choice in options, (choice, options)
        return choice

    def confirm(self, title):
        self.prompts.append(title)
        return next(self.confirmations)

    def page(self, text):
        self.pages.append(text)

    def row(self, *args):
        self.rows.append(args)


class WizardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.ArchiveIntegrationTests.setUpClass.__func__(cls)

    @classmethod
    def tearDownClass(cls):
        fixtures.ArchiveIntegrationTests.tearDownClass.__func__(cls)

    setUp = fixtures.ArchiveIntegrationTests.setUp
    tearDown = fixtures.ArchiveIntegrationTests.tearDown
    write = fixtures.ArchiveIntegrationTests.write

    def test_conflict_diff_and_source_choice_use_verified_apply(self):
        self.write(self.fi, '.shared', 'settings', 'desktop\n')
        self.write(self.li, '.shared', 'settings', 'laptop\n')
        self.fi.backup('.shared')
        ui=UI(['Resolve conflicts','Use source','Apply reviewed changes'],[True,False])
        setup(self.li,'fi',['.shared'],ui=ui)
        self.assertEqual((self.li.home/'.shared/settings').read_text(),'desktop\n')
        self.assertTrue(self.li.baseline_path('.shared','fi').exists())
        self.assertTrue(any('-laptop' in p and '+desktop' in p for p in ui.pages))

    def test_declined_apply_then_skip_writes_no_baseline_or_files(self):
        self.write(self.fi,'.shared','new','desktop')
        self.fi.backup('.shared')
        ui=UI(['Apply reviewed changes','Skip folder'],[False])
        setup(self.li,'fi',['.shared'],ui=ui)
        self.assertFalse((self.li.home/'.shared/new').exists())
        self.assertFalse(self.li.baseline_path('.shared','fi').exists())

    def test_keep_local_and_binary_conflict_are_supported(self):
        self.write(self.fi,'.shared','binary','desktop\0')
        self.write(self.li,'.shared','binary','laptop\0')
        self.fi.backup('.shared')
        ui=UI(['Resolve conflicts','Keep local','Apply reviewed changes'],[True,False])
        setup(self.li,'fi',['.shared'],ui=ui)
        self.assertEqual((self.li.home/'.shared/binary').read_text(),'laptop\0')
        self.assertTrue(any('Binary file' in p for p in ui.pages))

    def test_master_preview_and_confirmation_include_deletion(self):
        self.write(self.fi,'.master','new','desktop')
        self.write(self.li,'.master','old','laptop')
        self.fi.backup('.master')
        ui=UI(['Apply reviewed changes'],[True,False])
        setup(self.li,'fi',['.master'],ui=ui)
        self.assertIn('EXACT MIRROR',ui.prompts[0])
        self.assertTrue(any('DELETE   old' in p for p in ui.pages))
        self.assertFalse((self.li.home/'.master/old').exists())

    def test_change_during_review_is_not_overwritten(self):
        self.write(self.fi,'.shared','file','desktop')
        self.fi.backup('.shared')
        ui=UI(['Apply reviewed changes','Skip folder'])
        def confirm(title):
            self.write(self.li,'.shared','file','changed during review')
            return True
        ui.confirm=confirm
        setup(self.li,'fi',['.shared'],ui=ui)
        self.assertEqual((self.li.home/'.shared/file').read_text(),'changed during review')
        self.assertFalse(self.li.baseline_path('.shared','fi').exists())
        self.assertTrue(any('create a new plan' in p for p in ui.pages))

    def test_optional_backup_requires_confirmation_and_ready(self):
        self.config['folders']={'.shared':{'mode':'sync'}}
        self.fi.backup('.shared')
        ui=UI(['Apply reviewed changes'],[True,True])
        with patch.object(self.li,'backup',return_value={}) as backup:
            setup(self.li,'fi',ui=ui)
        backup.assert_called_once_with('.shared')

    def test_cancellation_before_apply_keeps_original_files(self):
        self.fi.backup('.shared')
        with self.assertRaises(KeyboardInterrupt):
            setup(self.li,'fi',['.shared'],ui=UI(['Quit']))
        self.assertFalse(self.li.baseline_path('.shared','fi').exists())

    def test_backup_only_folder_is_rejected_before_any_plans(self):
        with patch.object(self.li,'plan') as plan, self.assertRaises(ArchiveError):
            setup(self.li,'fi',['.shared','.device'],ui=UI([]))
        plan.assert_not_called()

    def test_terminal_control_sequences_are_escaped(self):
        self.assertEqual(visible('name\x1b[2J\r'),r'name\x1b[2J\x0d')
