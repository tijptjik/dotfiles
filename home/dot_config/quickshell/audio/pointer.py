import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "network"))
import network
import pointer
network.MODULE_KIND = "audio"
pointer.watch()
