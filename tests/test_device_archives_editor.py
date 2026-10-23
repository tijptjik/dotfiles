import unittest
from unittest.mock import patch
import test_device_archives as fixtures
from device_archives.editor import Decisions
from device_archives.core import ArchiveError
from device_archives.wizard import review_folder

class EditorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): fixtures.ArchiveIntegrationTests.setUpClass.__func__(cls)
    @classmethod
    def tearDownClass(cls): fixtures.ArchiveIntegrationTests.tearDownClass.__func__(cls)
    setUp = fixtures.ArchiveIntegrationTests.setUp
    tearDown = fixtures.ArchiveIntegrationTests.tearDown
    write = fixtures.ArchiveIntegrationTests.write

    def plan(self, folder='.shared'):
        self.write(self.fi,folder,'file','source')
        self.fi.backup(folder)
        return self.li.plan(folder,'fi')

    def test_revisit_reject_nonconflicting_addition_and_apply(self):
        path, plan = self.plan()
        d = Decisions(plan)
        d.set('file','accepted')
        d.set('file','rejected')
        self.li.apply(path,d.resolutions())
        self.assertFalse((self.li.home/'.shared/file').exists())
        self.assertTrue(self.li.baseline_path('.shared','fi').exists())

    def test_skipped_and_undecided_block_baseline(self):
        _,plan=self.plan()
        d=Decisions(plan)
        for state in ('pending','skipped'):
            d.set('file',state)
            with self.assertRaises(ArchiveError): d.resolutions()
        d.set('file','accepted')
        d.set('file','pending')
        with self.assertRaises(ArchiveError): d.resolutions()
        self.assertFalse(self.li.baseline_path('.shared','fi').exists())

    def test_master_rejection_is_blocked_in_editor_and_core(self):
        path,plan=self.plan('.master')
        with self.assertRaises(ArchiveError): Decisions(plan).set('file','rejected')
        with self.assertRaises(ArchiveError): self.li.apply(path,{'file':'local'})

    def test_declined_confirmation_preserves_decisions_for_revisit(self):
        self.plan()
        visits=[]
        class UI:
            def row(self,*args): pass
            def edit(self,review,decisions):
                visits.append(dict(decisions.states))
                self.preview=review.show('file')
                decisions.set('file','accepted' if len(visits)==1 else 'rejected')
                return 'apply'
            def confirm(self,title): return len(visits)==2
        ui=UI()
        self.assertTrue(review_folder(self.li,'.shared','fi',None,ui))
        self.assertEqual(visits,[{'file':'pending'},{'file':'accepted'}])
        self.assertIn('+source',ui.preview)
        self.assertFalse((self.li.home/'.shared/file').exists())

    def test_skipping_folder_never_applies_marked_decisions(self):
        self.plan()
        class UI:
            def row(self,*args): pass
            def edit(self,review,decisions):
                decisions.set('file','accepted')
                return 'skip'
        self.assertFalse(review_folder(self.li,'.shared','fi',None,UI()))
        self.assertFalse(self.li.baseline_path('.shared','fi').exists())

    def test_unknown_resolution_cannot_change_unreviewed_path(self):
        path,_=self.plan()
        with self.assertRaises(ArchiveError): self.li.apply(path,{'elsewhere':'source'})
