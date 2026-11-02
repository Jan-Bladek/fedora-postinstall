#!/usr/bin/env python3
"""Dependency-free curses fallback for the whiptail subset used by the installer."""
import curses
import os
import select
import sys
import textwrap


def option(args, flag, default):
    return args[args.index(flag)+1] if flag in args else default


def parse(args):
    kind = next(k for k in ('--radiolist', '--checklist', '--yesno', '--gauge') if k in args)
    start = args.index(kind)
    prompt = args[start+1]
    items = []
    if kind in ('--radiolist', '--checklist'):
        values = args[start+5:]
        if len(values) % 3:
            raise ValueError('Invalid item triples')
        items = [(values[i], values[i+1], values[i+2] == 'ON') for i in range(0, len(values), 3)]
    return kind, prompt, items


def paint(screen, title, prompt, lines, footer, cursor=-1, percent=None):
    screen.erase()
    height, width = screen.getmaxyx()
    if height < 10 or width < 45:
        screen.addnstr(0, 0, 'Powiększ terminal: minimum 45x10', max(1, width-1))
        screen.refresh()
        return
    screen.attron(curses.color_pair(1))
    screen.addnstr(1, 3, 'FEDORA POST-INSTALL', width-6, curses.A_BOLD)
    screen.addnstr(2, 3, title, width-6)
    screen.attroff(curses.color_pair(1))
    row = 4
    for line in textwrap.wrap(prompt, width-8)[:max(1, height//3)]:
        screen.addnstr(row, 4, line, width-8)
        row += 1
    row += 1
    space = max(1, height-row-3)
    top = max(0, cursor-space+1) if cursor >= 0 else 0
    for index, line in enumerate(lines[top:top+space], top):
        style = curses.A_REVERSE if index == cursor else curses.A_NORMAL
        screen.addnstr(row+index-top, 4, line, width-8, style)
    if percent is not None:
        count = width-10
        filled = count*max(0, min(100, percent))//100
        bar = '['+'#'*filled+' '*(count-filled)+f'] {percent}%'
        screen.addnstr(height-4, 4, bar, width-8, curses.color_pair(1))
    screen.addnstr(height-2, 3, footer, width-6, curses.A_DIM)
    screen.refresh()


def dialog(screen, args, incoming):
    curses.curs_set(0)
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_CYAN, -1)
    kind, prompt, items = parse(args)
    title = option(args, '--title', 'Instalator')
    yes = option(args, '--yes-button', 'Dalej')
    no = option(args, '--no-button', 'Anuluj')
    cursor = 0
    selected = {key for key, _, on in items if on}
    if kind == '--gauge':
        buffer, block, percent, message = '', None, 0, prompt
        while True:
            paint(screen, title, message, [], 'Postęp oznacza ukończone etapy. Szczegóły są zapisywane w logu.', percent=percent)
            ready, _, _ = select.select([incoming], [], [], 0.2)
            if not ready:
                continue
            chunk = os.read(incoming, 65536)
            if not chunk:
                return 0, ''
            buffer += chunk.decode(errors='replace')
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                if line == 'XXX':
                    if block is not None:
                        if block and block[0].isdigit():
                            percent = int(block[0])
                            message = '\n'.join(block[1:])
                        block = None
                    else:
                        block = []
                elif block is not None:
                    block.append(line)
                elif line.isdigit():
                    percent = int(line)
    while True:
        if kind == '--yesno':
            lines = ['  '+yes, '  '+no]
        else:
            lines = [('(*) ' if key in selected else '( ) ') + label if kind == '--radiolist'
                     else ('[x] ' if key in selected else '[ ] ') + label for key, label, _ in items]
        paint(screen, title, prompt, lines, '↑/↓ wybór · Spacja zaznacza · Enter dalej · Esc anuluje', cursor)
        key = screen.getch()
        if key in (27, ord('q')):
            return 1, ''
        if key in (curses.KEY_UP, ord('k')):
            cursor = max(0, cursor-1)
        elif key in (curses.KEY_DOWN, ord('j')):
            cursor = min(len(lines)-1, cursor+1)
        elif key == ord(' ') and items:
            value = items[cursor][0]
            if kind == '--radiolist':
                selected = {value}
            elif value in selected:
                selected.remove(value)
            else:
                selected.add(value)
        elif key in (10, 13, curses.KEY_ENTER):
            if kind == '--yesno':
                return (0 if cursor == 0 else 1), ''
            if kind == '--radiolist':
                return 0, items[cursor][0]
            return 0, '\n'.join(key for key, _, _ in items if key in selected)


def main():
    # whiptail writes results to stderr, while its UI uses the real terminal.
    # Preserve the original gauge pipe before attaching curses to /dev/tty.
    incoming, result_fd = os.dup(0), os.dup(2)
    terminal = os.open('/dev/tty', os.O_RDWR)
    for fd in (0, 1, 2):
        os.dup2(terminal, fd)
    try:
        code, result = curses.wrapper(dialog, sys.argv[1:], incoming)
        if result:
            os.write(result_fd, (result+'\n').encode())
        return code
    finally:
        os.close(terminal)
        os.close(incoming)
        os.close(result_fd)


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
