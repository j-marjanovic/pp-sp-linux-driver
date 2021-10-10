import curses
from abc import ABC, abstractmethod


class MessagePane:
    def __init__(self, nlines: int, ncols: int, begin_y: int, begin_x: int):
        self.lines = [str(idx) * 10 for idx in range(nlines - 2)]

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
        del self.lines[0]
        self.lines.append(msg)
        self.refresh()


class Bar:
    def __init__(
        self, nlines: int, ncols: int, begin_y: int, begin_x: int, max_val: float
    ):
        self.txt = ""
        self.fill_perc = 0
        self.max_val = max_val

        self.win = curses.newwin(nlines, ncols, begin_y, begin_x)
        self.win.border()
        self.win.bkgd(" ", curses.color_pair(2) | curses.A_BOLD)
        self.win.refresh()
        self.refresh()

    def set_value(self, val: float):
        self.txt = f" {val} MB/s"
        self.fill_perc = val * 100 / self.max_val
        self.refresh()

    def refresh(self):
        h, w = self.win.getmaxyx()
        w_fill = (w - 2) * self.fill_perc // 100

        for i in range(1, w - 1):
            try:
                ch = self.txt[i - 1]
            except IndexError:
                ch = " "

            color = curses.color_pair(6) if i <= w_fill else curses.color_pair(2)
            self.win.addch(1, i, ch, color)

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
        self.els = ["Idle", "Read", "Write"]
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
        elif char in (curses.KEY_ENTER, "\n"):
            self.sel = self.sel_highlight

    def set_highlight(self, highlighted):
        self.highlight = highlighted


class TransferSizeSel(ControlElement):
    # TODO: limits
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
        if char == curses.KEY_DOWN:  # TODO: check limits
            self.size //= 2
        elif char == curses.KEY_UP:  # TODO: check limits
            self.size *= 2

    def set_highlight(self, highlighted):
        self.highlight = highlighted
