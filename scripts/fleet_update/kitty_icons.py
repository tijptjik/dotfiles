"""Two-line fleet rows for Kitty 0.40+: 32px sprites and centred normal-size text.

Unicode image placeholders belong to the text grid, so scrolling and the
progress renderer's line erasure also move/remove the visible images. Quiet,
inline transmission works through the runner's pipes and SSH without replies.
See https://sw.kovidgoyal.net/kitty/graphics-protocol/#unicode-placeholders and
https://sw.kovidgoyal.net/kitty/text-sizing-protocol/ .
"""
import base64
import fcntl
import json
import math
import os
from pathlib import Path
import re
import select
import secrets
import struct
import sys
import termios
import time
import zlib

from tjikup import runtime
from tjikup.progress import changed_spans
from .icon_catalog import SPRITE_ALIASES, display_title

SGR = re.compile(r'\x1b\[[0-9;]*m')
DIACRITICS = '\u0305\u030d\u030e\u0310\u0312\u033d\u033e\u033f'


def in_herdr():
    return os.environ.get('HERDR_ENV') == '1' and os.environ.get('TERM_PROGRAM') == 'herdr'


def herdr_cell_size(stream):
    """Herdr PTYs omit pixels from ioctl; its VT answers the cell-size query.

    Query only at renderer startup, before hooks can prompt. Refuse to read a
    terminal with pending input, and restore its modes even on timeout/error.
    stderr remains attached when Tjikup forwards stdout through detached workers.
    """
    for file in (stream, sys.stderr):
        try:
            path = os.ttyname(file.fileno())
            break
        except (OSError, ValueError, AttributeError):
            continue
    else:
        return None
    fd = None
    original = None
    try:
        fd = os.open(path, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
        original = termios.tcgetattr(fd)
        mode = termios.tcgetattr(fd)
        mode[3] &= ~(termios.ICANON | termios.ECHO)
        mode[6][termios.VMIN], mode[6][termios.VTIME] = 0, 0
        termios.tcsetattr(fd, termios.TCSANOW, mode)
        if select.select([fd], [], [], 0)[0]:
            return None
        os.write(fd, b'\x1b[16t')
        response = bytearray()
        deadline = time.monotonic() + .2
        while len(response) < 32:
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not select.select([fd], [], [], remaining)[0]:
                return None
            response.extend(os.read(fd, 1))
            if response.endswith(b't'):
                match = re.fullmatch(rb'\x1b\[6;([0-9]+);([0-9]+)t', response)
                if match:
                    height, width = map(int, match.groups())
                    if 4 <= width <= 128 and 16 <= height <= 256:
                        return width, height
                return None
        return None
    except (OSError, termios.error):
        return None
    finally:
        if fd is not None:
            try:
                if original is not None:
                    termios.tcsetattr(fd, termios.TCSANOW, original)
            except (OSError, termios.error):
                pass
            finally:
                os.close(fd)


def cell_size(stream):
    """Read geometry without terminal queries that could consume keyboard input."""
    def read_size(file):
        try:
            geometry = fcntl.ioctl(file.fileno(), termios.TIOCGWINSZ, bytes(8))
        except (OSError, ValueError, AttributeError):
            return None
        rows, columns, width, height = struct.unpack('HHHH', geometry)
        if all((rows, columns, width, height)):
            return width // columns, height // rows
        return None

    # run_stream pipes stdout and starts a new session, but deliberately keeps
    # stderr attached to the terminal. /dev/tty alone cannot handle that path.
    for file in (stream, sys.stderr):
        size = read_size(file)
        if size:
            return size
    # Buffered DAG children have neither inherited terminal fds nor /dev/tty.
    # The parent renderer supplies geometry after checking terminal support.
    hint = re.fullmatch(r'(\d+)x(\d+)', os.environ.get('TJIKUP_CELL_SIZE', ''))
    if hint:
        width, height = map(int, hint.groups())
        if 4 <= width <= 128 and 16 <= height <= 256:
            return width, height
    try:
        with open('/dev/tty', 'rb') as tty:
            return read_size(tty)
    except OSError:
        return None


def styled_cells(text):
    """Keep SGR alongside each cell, without passing escapes into OSC payloads."""
    cells, style, offset = [], '', 0
    for match in SGR.finditer(text):
        cells.extend((char, style) for char in text[offset:match.start()])
        style = '' if match.group() == '\x1b[0m' else style + match.group()
        offset = match.end()
    cells.extend((char, style) for char in text[offset:])
    return cells


def centred(cells):
    """Fit pairs of normal-size cells into a vertically centred 2x2 block."""
    result, text, width, style = [], '', 0, ''

    def emit():
        result.append(style + '\x1b]66;s=2:n=1:d=2:v=2:w=1;' + text + ' ' * (2 - width) + '\x1b\\\x1b[0m')

    for char, colour in cells:
        size = runtime.display_width(char)
        if width + size > 2:
            emit()
            text, width = '', 0
        if not text or not text.strip():
            style = colour
        text += char
        width += size
    if text:
        emit()
    return ''.join(result)


def normal_text(cells):
    """Herdr 0.9.x renders ordinary cells but drops Kitty's OSC 66 text."""
    result, previous = [], None
    for char, style in cells:
        if style != previous:
            result.append('\x1b[0m' + style)
            previous = style
        result.append(char)
    return ''.join(result) + '\x1b[0m'


class KittyIcons:
    def __init__(self, stream, *, geometry=None, herdr=False):
        self.stream = stream
        self.images = {}
        self.sprites = None
        self.geometry = geometry
        self.herdr = herdr

    @classmethod
    def available(cls, stream, live):
        if os.environ.get('TJIKUP_ICONS') == '0' or os.environ.get('TJIKUP_KITTY_ICONS') == '0':
            return None
        herdr = in_herdr()
        if (os.environ.get('TERM') != 'xterm-kitty' and not herdr) or os.environ.get('TMUX') or os.environ.get('STY'):
            return None
        if not (stream.isatty() or live or runtime.use_color()):
            return None
        size = cell_size(stream)
        if size is None and herdr:
            size = herdr_cell_size(stream)
        if size is None or size[0] < 4 or size[1] < 16:
            return None
        return cls(stream, geometry=size, herdr=herdr)

    def image(self, label, cell_width, cell_height):
        label = SPRITE_ALIASES.get(label, label)
        if self.sprites is None:
            self.sprites = json.loads(Path(__file__).with_name('icons32.json').read_text())['sprites']
        key = label if label in self.sprites else label.partition(' (')[0]
        key = key if key in self.sprites else '*'
        # Even column count keeps the centred text's two-cell blocks aligned.
        columns = 2 * math.ceil(32 / (2 * cell_width))
        cache_key = (key, cell_width, cell_height)
        if cache_key not in self.images:
            width, height = columns * cell_width, 2 * cell_height
            source = zlib.decompress(base64.b64decode(self.sprites[key]))
            canvas = bytearray(width * height * 4)
            left = (width - 32) // 2
            top = max(0, ((cell_height if self.herdr else height) - 32) // 2)
            for row in range(32):
                start = ((top + row) * width + left) * 4
                canvas[start:start + 128] = source[row * 128:(row + 1) * 128]
            image_id = secrets.randbelow(0xffffff) + 1
            while image_id in self.images.values():
                image_id = secrets.randbelow(0xffffff) + 1
            data = base64.b64encode(zlib.compress(canvas)).decode()
            for offset in range(0, len(data), 4096):
                chunk = data[offset:offset + 4096]
                header = (f'a=T,f=32,o=z,s={width},v={height},i={image_id},U=1,c={columns},r=2,q=2,'
                          if offset == 0 else '')
                self.stream.write(f'\x1b_G{header}m={int(offset + 4096 < len(data))};{chunk}\x1b\\')
            self.images[cache_key] = image_id
        return self.images[cache_key], columns

    @staticmethod
    def placeholders(image_id, columns, row):
        colour = f'\x1b[38;2;{image_id >> 16};{(image_id >> 8) & 255};{image_id & 255}m'
        return colour + ''.join('\U0010eeee' + DIACRITICS[row] + DIACRITICS[column]
                                for column in range(columns)) + '\x1b[0m'

    def print(self, verb, icon, label, note):
        size = cell_size(self.stream) or self.geometry
        if size is None or size[0] < 4 or size[1] < 16:
            # Keep the two-line height during a temporary loss of geometry.
            self.stream.write(runtime.format_status(verb, icon, display_title(label), note) + '\n\n')
            return
        image_id, columns = self.image(label, *size)
        # The status prefix already leaves one cell before the image canvas.
        # Reserve the same gap after it, including in narrow-row truncation.
        row = runtime.format_status(verb, icon, ' ' * (columns + 1) + display_title(label), note)
        prefix_width = len(f'{verb:<7} {icon} ')
        self._print_row(row, image_id, columns, prefix_width)

    def patch(self, before, after):
        """Patch text blocks without erasing or repainting either image row."""
        size = cell_size(self.stream) or self.geometry
        graphics = size is not None and size[0] >= 4 and size[1] >= 16
        columns = 2 * math.ceil(32 / (2 * size[0])) if graphics else 0

        def row(fields):
            verb, icon, label, note = fields
            title = display_title(label)
            if graphics:
                title = ' ' * (columns + 1) + title
            return runtime.format_status(verb, icon, title, note)

        text = normal_text if self.herdr or not graphics else centred
        return ''.join(f'\033[{column + 1}G' + text(cells)
                       for column, cells in changed_spans(row(before), row(after),
                                                          group=1 if self.herdr or not graphics else 2))

    def print_text(self, label, row):
        """Repository operation cells keep their colours beside one title icon."""
        size = cell_size(self.stream) or self.geometry
        if size is None or size[0] < 4 or size[1] < 16:
            self.stream.write(row + '\n\n')
            return
        image_id, columns = self.image(label, *size)
        self._print_row(' ' * columns + ' ' + row, image_id, columns, 0)

    def _print_row(self, row, image_id, columns, prefix_width):
        cells = styled_cells(row)
        text = normal_text if self.herdr else centred
        self.stream.write(text(cells[:prefix_width]))
        self.stream.write(self.placeholders(image_id, columns, 0))
        self.stream.write(text(cells[prefix_width + columns:]))
        # CSI 0 C means move ONE column, not zero. Repository icons start
        # at column zero, so their second placeholder row needs no movement.
        indent = f'\x1b[{prefix_width}C' if prefix_width else ''
        self.stream.write('\r\n' + indent + self.placeholders(image_id, columns, 1) + '\r\n')
