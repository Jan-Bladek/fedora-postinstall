#!/usr/bin/env python3
"""Show installation progress, with P toggling the unmodified live log."""
import argparse
import curses
import os
from pathlib import Path
import select
import signal
import sys
import termios
import tty

from tui import paint


class Progress:
    def __init__(self, run, desktop):
        self.run = run
        self.desktop = desktop
        self.screen = None
        self.offset = 0

    def pretty(self):
        self.screen = curses.initscr()
        curses.noecho()
        curses.cbreak()
        try:
            curses.curs_set(0)
        except curses.error:
            pass
        try:
            curses.start_color()
            curses.use_default_colors()
            curses.init_pair(1, curses.COLOR_CYAN, -1)
        except curses.error:
            self.details()
            return
        self.screen.clear()

    def details(self):
        curses.endwin()
        self.screen = None
        tty.setcbreak(sys.stdin.fileno())
        print('\nSzczegóły instalacji — P: powrót do widoku postępu\n', flush=True)

    def stream_log(self):
        try:
            with (self.run / 'install.log').open('rb') as log:
                log.seek(self.offset)
                data = log.read(65536)
        except FileNotFoundError:
            return False
        if data:
            sys.stdout.buffer.write(data)
            sys.stdout.buffer.flush()
            self.offset += len(data)
        return bool(data)

    def draw(self):
        size = os.get_terminal_size(sys.stdin.fileno())
        if self.screen.getmaxyx() != (size.lines, size.columns):
            curses.resizeterm(size.lines, size.columns)
        try:
            percent = int((self.run / 'progress-percent').read_text().strip() or '0')
        except (FileNotFoundError, ValueError):
            percent = 0
        try:
            status = (self.run / 'progress-status').read_text()
        except FileNotFoundError:
            status = 'Przygotowanie'
        paint(self.screen, 'Instalacja · ' + self.desktop,
              status + '\n\nLog: ' + str(self.run / 'install.log'), [],
              'P: szczegóły  |  Ctrl+C: przerwij', percent=percent)

    def watch(self, parent):
        original = termios.tcgetattr(sys.stdin.fileno())
        try:
            if (self.run / 'progress-done').exists():
                return
            self.pretty()
            while os.getppid() == parent and not (self.run / 'progress-done').exists():
                if self.screen is None:
                    self.stream_log()
                else:
                    self.draw()
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    keys = os.read(sys.stdin.fileno(), 1024)
                    if not keys:
                        break
                    for key in keys:
                        if key in (ord('p'), ord('P')):
                            if self.screen is None:
                                self.pretty()
                            else:
                                self.details()
            if self.screen is None:
                while self.stream_log():
                    pass
        finally:
            try:
                curses.endwin()
            except curses.error:
                pass
            termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, original)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    parser.add_argument('desktop')
    parser.add_argument('parent', type=int)
    args = parser.parse_args()
    signal.signal(signal.SIGINT, signal.default_int_handler)
    def stop(signum, frame):
        raise SystemExit(0)
    signal.signal(signal.SIGTERM, stop)
    try:
        Progress(args.run, args.desktop).watch(args.parent)
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == '__main__':
    sys.exit(main())
