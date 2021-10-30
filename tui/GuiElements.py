import curses
from abc import ABC, abstractmethod

import numpy as np


class MessagePane:
    def __init__(self, nlines: int, ncols: int, begin_y: int, begin_x: int):
        self.lines = []  # str(idx) * 10 for idx in range(nlines - 2)]
        self.nlines = nlines

        self.win = curses.newwin(nlines, ncols, begin_y, begin_x)
        self.win.border()
        self.win.bkgd(" ", curses.color_pair(1))
        self.win.refresh()

    def set_title(self, title):
        title = " " + title + " "
        h, w = self.win.getmaxyx()
        self.win.addstr(0, w // 2 - len(title) // 2, title, curses.A_BOLD)
        self.win.refresh()

    def refresh(self):
        h, w = self.win.getmaxyx()

        for idx, line in enumerate(self.lines):
            self.win.addstr(1 + idx, 1, line.ljust(w - 2))

        self.win.refresh()

    def append_msg(self, msg):
        self.lines.append(msg)
        if len(self.lines) > self.nlines - 2:
            del self.lines[0]
        self.refresh()


class Bar:
    def __init__(
        self, nlines: int, ncols: int, begin_y: int, begin_x: int, max_val: float
    ):
        self.txt = ""
        self.fill_perc = 0
        self.max_val = max_val
        self.prev_vals = []
        self.stats_txt = ""

        self.win = curses.newwin(nlines, ncols, begin_y, begin_x)
        self.win.border()
        self.win.bkgd(" ", curses.color_pair(2) | curses.A_BOLD)
        self.win.refresh()
        self.refresh()

    def set_value(self, val: float):
        self.txt = f" {val:8.2f} MB/s"
        self.fill_perc = val * 100 / self.max_val
        self.prev_vals.append(val)
        if len(self.prev_vals) > 100:
            del self.prev_vals[0]

        prev_vals_np = np.array(self.prev_vals)
        stats_min = np.min(prev_vals_np)
        stats_max = np.max(prev_vals_np)
        stats_mean = np.mean(prev_vals_np)

        self.stats_txt = (
            f"{stats_min:7.2f} MB/s | {stats_mean:7.2f} MB/s | {stats_max:7.2f} MB/s"
        )
        val_min = np.min(self.prev_vals)
        self.refresh()

    def refresh(self):
        h, w = self.win.getmaxyx()
        w_fill = int((w - 2) * self.fill_perc / 100)

        txt = self.txt.ljust(w - 2)
        self.win.addstr(1, 1, txt[:w_fill], curses.color_pair(6))
        self.win.addstr(1, 1 + w_fill, txt[w_fill:], curses.color_pair(2))

        self.win.addstr(2, 1, self.stats_txt)
        self.win.refresh()


class ControlElement(ABC):
    @abstractmethod
    def cmd(self, char):
        ...

    @abstractmethod
    def refresh(self):
        ...

    @abstractmethod
    def set_highlight(self, highlighted):
        ...


class RadioList(ControlElement):
    def __init__(self, nlines: int, ncols: int, begin_y: int, begin_x: int):
        self.els = ["Idle", "Write", "Read"]
        self.sel = 0
        self.highlight = False
        self.sel_highlight = 0

        self.win = curses.newwin(nlines, ncols, begin_y, begin_x)
        self.win.border()
        self.win.bkgd(" ", curses.color_pair(2))
        self.win.refresh()
        self.refresh()

    def refresh(self):
        h, w = self.win.getmaxyx()

        for idx, el in enumerate(self.els):
            s = f"({'x' if self.sel == idx else ' '}) {el}".ljust(w - 2)

            color = (
                curses.color_pair(5)
                if self.highlight and self.sel_highlight == idx
                else curses.color_pair(4)
            )
            self.win.addstr(1 + idx, 1, s, color)
            self.win.refresh()

    def cmd(self, char):
        if char == curses.KEY_DOWN and self.sel_highlight < len(self.els) - 1:
            self.sel_highlight += 1
        elif char == curses.KEY_UP and self.sel_highlight > 0:
            self.sel_highlight -= 1
        elif char in (curses.KEY_ENTER, ord("\n")):
            self.sel = self.sel_highlight
        self.refresh()

    def set_highlight(self, highlighted):
        self.highlight = highlighted


class TransferSizeSel(ControlElement):
    def __init__(self, nlines: int, ncols: int, begin_y: int, begin_x: int):
        self.size = 1024
        self.highlight = False

        self.win = curses.newwin(nlines, ncols, begin_y, begin_x)
        self.win.border()
        self.win.bkgd(" ", curses.color_pair(2))
        self.win.refresh()
        self.refresh()

    def refresh(self):
        h, w = self.win.getmaxyx()

        prefixes = [
            (1024 * 1024 * 1024, "Gi"),
            (1024 * 1024, "Mi"),
            (1024, "Ki"),
            (1, ""),
        ]

        for prefix in prefixes:
            if self.size >= prefix[0]:
                str_prefix = prefix[1]
                size = self.size // prefix[0]
                break

        s = f"{size} {str_prefix}B".rjust(w - 2)

        color = curses.color_pair(5) if self.highlight else curses.color_pair(4)
        self.win.addstr(1, 1, s, color)
        self.win.refresh()

    def cmd(self, char):
        if char == curses.KEY_DOWN:
            if self.size > 128:
                self.size //= 2
        elif char == curses.KEY_UP:
            if self.size < 4 * 1024 * 1024:
                self.size *= 2

    def set_highlight(self, highlighted):
        self.highlight = highlighted
