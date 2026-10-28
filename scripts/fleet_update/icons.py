"""Fleet title icons; colour images in Kitty, compact Nerd Font fallback."""
import os

from tjikup import runtime
from tjikup.progress import Progress


from .icon_catalog import ASSET_ICONS, SERVICE_ICONS
from .kitty_icons import KittyIcons


def icons_enabled(stream, live):
    setting = os.environ.get("TJIKUP_ICONS")
    return setting == "1" if setting is not None else (
        os.environ.get("TERM") != "dumb"
        and (live or stream.isatty() or runtime.use_color())
    )


def title_icon(label):
    service, _, subtype = label.partition(" (")
    if service == "Assets":
        return ASSET_ICONS.get(subtype.rstrip(")"), SERVICE_ICONS[service])
    return SERVICE_ICONS.get(service, "\uf013")


class HookProgress(Progress):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.graphics = KittyIcons.available(self.stream, self.live)

    def _draw(self):
        super()._draw()
        if self.graphics:
            self.height *= 2

    def _print(self, verb, icon, label, note):
        if self.graphics:
            self.graphics.print(verb, icon, label, note)
            return
        if icons_enabled(self.stream, self.live):
            label = f"{title_icon(label)} {label}"
        super()._print(verb, icon, label, note)
