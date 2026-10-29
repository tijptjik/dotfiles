"""Revisitable two-pane terminal review; no filesystem writes before apply."""
import curses
import textwrap

from .core import ArchiveError, merge_entries


class Decisions:
    def __init__(self, plan):
        self.plan = plan
        self.names = sorted(name for name in set(plan['local']) | set(plan['incoming'])
                            if plan['local'].get(name) != plan['incoming'].get(name))
        self.states = {name: 'pending' for name in self.names}

    def set(self, name, state):
        if state not in ('pending', 'accepted', 'rejected', 'skipped'):
            raise ArchiveError('Invalid review decision')
        if self.plan['policy']['mode'] == 'master' and state == 'rejected':
            raise ArchiveError('Exact mirror: accept source or skip this folder')
        self.states[name] = state

    def resolutions(self):
        pending = [name for name, state in self.states.items() if state in ('pending', 'skipped')]
        if pending:
            raise ArchiveError(f'{len(pending)} pending/skipped files: decide them or skip the folder')
        return {name: 'source' if state == 'accepted' else 'local' for name, state in self.states.items()}

    def changes(self):
        return merge_entries(self.plan['base'], self.plan['local'], self.plan['incoming'],
                             self.plan['policy']['mode'] == 'master', self.resolutions())


HELP = '''REVIEW SHORTCUTS

Up/Down or j/k   Select a file; revisit any previous decision
Tab              Switch focus between file list and preview
PgUp/PgDn        Scroll preview (also J/K)
Home/End         First/last file, or preview top/bottom

a                Accept source version from fi
r                Reject source; keep local version
s                Mark skipped (defer this file)
u                Undo decision; mark pending
A                Accept all pending files (decisions can be changed)
Enter            Continue to folder confirmation
S                Skip whole folder without applying anything
q or Esc         Quit without applying this folder
?                Show/hide this help

Skipped and pending files block applying the folder. Revisit them or
skip the whole folder; partial decisions never create a sync baseline.
Exact-mirror folders allow source acceptance only; skip to preserve local.
No changes are written until you confirm after leaving this editor.
'''


def run_editor(review, decisions, sanitize):
    def run(screen):
        curses.curs_set(0)
        screen.keypad(True)
        index = offset = top = 0
        focus = 'files'
        help_open = False
        message = ''
        cache = {}

        def put(y, x, text, width, attr=0):
            try:
                screen.addnstr(y, x, text, max(0, width), attr)
            except curses.error:
                pass

        while True:
            height, width = screen.getmaxyx()
            screen.erase()
            if height < 10 or width < 60:
                put(0, 0, 'Resize terminal to at least 60 columns x 10 rows; q quits.', width-1)
                screen.refresh()
                key = screen.getch()
                if key in (ord('q'), 27):
                    raise KeyboardInterrupt
                continue
            left = min(48, max(24, width // 3))
            body = height - 6
            name = decisions.names[index] if decisions.names else None
            counts = {state: list(decisions.states.values()).count(state)
                      for state in ('pending', 'accepted', 'rejected', 'skipped')}
            title = f"{review.plan['source']} -> {review.plan['machine']}  {review.plan['folder']}"
            if review.plan['policy']['mode'] == 'master':
                title += '  EXACT MIRROR'
            put(0, 0, sanitize(title), width-1, curses.A_BOLD)
            put(1, 0, '  '.join(f'{s}: {n}' for s, n in counts.items()), width-1)
            put(2, 0, 'FILES' + (' [focus]' if focus == 'files' else ''), left-1, curses.A_BOLD)
            put(2, left+1, 'PREVIEW' + (' [focus]' if focus == 'preview' else ''), width-left-2, curses.A_BOLD)
            if index < top:
                top = index
            if index >= top + body:
                top = index-body+1
            for row, entry in enumerate(decisions.names[top:top+body], 3):
                label = f"[{decisions.states[entry]}] {sanitize(entry).replace(chr(10), r'\n').replace(chr(9), r'\t')}"
                put(row, 0, label, left-1, curses.A_REVERSE if entry == name else 0)
            for row in range(2, height-3):
                put(row, left, '|', 1)
            if help_open:
                content = HELP
            elif name:
                if name not in cache:
                    put(3, left+1, 'Loading verified preview…', width-left-2)
                    screen.refresh()
                    cache[name] = sanitize(review.show(name)).expandtabs(4)
                content = f"Decision: {decisions.states[name]}\n" + cache[name]
            else:
                content = 'No differing files. Enter records the sync baseline.'
            lines = []
            for line in content.splitlines():
                lines.extend(textwrap.wrap(line, max(1, width-left-3), replace_whitespace=False) or [''])
            offset = min(offset, max(0, len(lines)-body))
            for row, line in enumerate(lines[offset:offset+body], 3):
                put(row, left+1, line, width-left-2)
            put(height-3, 0, sanitize(message), width-1, curses.A_BOLD)
            put(height-2, 0, 'a accept  r reject  s skip  u undo  Enter review/apply  ? help', width-1)
            put(height-1, 0, 'Tab focus  PgUp/PgDn preview  A accept pending  S skip folder  q quit', width-1)
            screen.refresh()
            key = screen.getch()
            message = ''
            if key == curses.KEY_RESIZE:
                continue
            if key == ord('?'):
                help_open = not help_open
                offset = 0
                continue
            if help_open:
                if key in (27, ord('q')):
                    help_open = False
                    offset = 0
                elif key in (curses.KEY_DOWN, ord('j'), curses.KEY_NPAGE):
                    offset += body if key == curses.KEY_NPAGE else 1
                elif key in (curses.KEY_UP, ord('k'), curses.KEY_PPAGE):
                    offset = max(0, offset-(body if key == curses.KEY_PPAGE else 1))
                continue
            if key in (ord('q'), 27):
                raise KeyboardInterrupt
            if key == ord('S'):
                return 'skip'
            if key == 9:
                focus = 'preview' if focus == 'files' else 'files'
            elif key in (curses.KEY_NPAGE, ord('J')):
                offset += body
            elif key in (curses.KEY_PPAGE, ord('K')):
                offset = max(0, offset-body)
            elif key in (curses.KEY_UP, ord('k'), curses.KEY_DOWN, ord('j'), curses.KEY_HOME, curses.KEY_END):
                if focus == 'preview':
                    offset = (0 if key == curses.KEY_HOME else len(lines) if key == curses.KEY_END
                              else max(0, offset + (-1 if key in (curses.KEY_UP, ord('k')) else 1)))
                else:
                    index = (0 if key == curses.KEY_HOME else max(0,len(decisions.names)-1) if key == curses.KEY_END
                             else max(0,min(len(decisions.names)-1,index+(-1 if key in (curses.KEY_UP,ord('k')) else 1))))
                    offset = 0
            elif key in (10, 13, curses.KEY_ENTER):
                try:
                    _, _, conflicts = decisions.changes()
                    if conflicts:
                        raise ArchiveError('Choices conflict structurally; revisit parent/child decisions')
                    return 'apply'
                except ArchiveError as error:
                    message = str(error)
            elif key == ord('A'):
                for entry, state in decisions.states.items():
                    if state == 'pending':
                        decisions.set(entry, 'accepted')
            elif name and key in map(ord, 'arsu'):
                try:
                    decisions.set(name, {ord('a'):'accepted',ord('r'):'rejected',ord('s'):'skipped',ord('u'):'pending'}[key])
                except ArchiveError as error:
                    message = str(error)
    return curses.wrapper(run)
