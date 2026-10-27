"""Contracts for the original Rose Punk launcher-command companion objects."""
import hashlib
import json
from pathlib import Path
import re
import sys
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts/icons'))
import command_icons
import fullset


class CommandIconTests(unittest.TestCase):
    def test_every_launcher_control_has_one_original_and_bindings_shares_shortcuts(self):
        manifest = json.loads((ROOT/'scripts/icons/command-icons.json').read_text())
        commands = {command: key for key, entry in manifest.items() for command in entry['commands']}
        self.assertEqual(set(commands), {'/refresh','/pin','/grid','/list','/stats','/config','/shortcuts','/bindings'})
        self.assertEqual(len(manifest), 8)
        self.assertEqual({key for key,entry in manifest.items() if entry['role']=='shell'}, {'fish'})
        self.assertEqual(commands['/bindings'], commands['/shortcuts'])

    def test_sources_and_generated_theme_are_identical_self_contained_vectors(self):
        outputs, manifest = command_icons.render()
        for key, entry in manifest.items():
            with self.subTest(icon=key):
                source = (ROOT/entry['source']).read_bytes()
                self.assertEqual(hashlib.sha256(source).hexdigest(), entry['sha256'])
                self.assertEqual(source, outputs[key+'.svg'])
                self.assertEqual(source, (command_icons.DEST/(key+'.svg')).read_bytes())
                root = ET.fromstring(source)
                self.assertEqual(root.get('viewBox'), '0 0 64 64')
                self.assertFalse({'image','script','foreignObject','text','filter'} & {n.tag.rsplit('}',1)[-1] for n in root.iter()})
                self.assertFalse(any(n.get('id') == 'tile' for n in root.iter()))
                ids = [n.get('id') for n in root.iter() if n.get('id')]
                self.assertEqual(len(ids),len(set(ids)))
                self.assertTrue(set(re.findall(r'url\(#([^)]*)\)',source.decode())) <= set(ids))
                for n in root.iter():
                    self.assertFalse(any('href' in attr for attr in n.attrib))
                left,top,right,bottom = entry['sizing']['result_bounds']
                self.assertGreaterEqual(min(left,top),3.75)
                self.assertLessEqual(max(right,bottom),60.25)
                self.assertGreaterEqual(max(right-left,bottom-top),49.5)
                self.assertLessEqual(max(right-left,bottom-top),56.5)

    def test_main_renderer_preserves_companions_during_full_rebuild(self):
        with patch.object(fullset,'load_catalog',return_value={}), patch.object(fullset,'aliases_for',return_value={}):
            outputs, aliases = fullset.render()
        expected, _ = command_icons.render()
        self.assertEqual(outputs,expected)
        self.assertEqual(aliases,{})

    def test_preview_has_unique_ids(self):
        preview = ROOT/'.local/icon-reviews/docs/rose-punk-command-icons.svg'
        if not preview.exists():
            self.skipTest('Optional local review has not been generated')
        root = ET.parse(preview).getroot()
        ids = [n.get('id') for n in root.iter() if n.get('id')]
        self.assertEqual(len(ids),len(set(ids)))
        self.assertTrue(set(re.findall(r'url\(#([^)]*)\)',preview.read_text())) <= set(ids))
