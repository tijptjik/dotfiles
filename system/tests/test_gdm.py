"""Host-specific native login policy."""
import configparser,json,os,sys,subprocess,tempfile
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tests'))
import native_render
ROOT=Path(__file__).resolve().parents[1]
class GdmTests(unittest.TestCase):
    def test_host_autologin_users(self):
        for host,user in [('fi','io'),('li','io'),('si','m')]:
            with tempfile.TemporaryDirectory() as tmp:
                config=Path(tmp)/'config.json'
                config.write_text(json.dumps({'data':{'isDesktop':host=='fi','isLaptop':host=='li','isClient':host!='si','isServer':host=='si'}}))
                rendered=subprocess.check_output(['render-native','--config',str(config),'-f',str(ROOT/f'native/{host}/files/gdm/custom.conf.j2')],text=True)
                parsed=configparser.ConfigParser();parsed.read_string(rendered)
                self.assertTrue(parsed.getboolean('daemon','AutomaticLoginEnable'))
                self.assertEqual(parsed.get('daemon','AutomaticLogin'),user)
