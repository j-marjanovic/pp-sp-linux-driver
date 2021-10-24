import curses
import datetime
import queue
import time

from GuiElements import Bar, MessagePane, RadioList, TransferSizeSel
from QueueMsg import Mode, MsgCmd, MsgResp
from PcieStats import PcieStatsResult


class Gui:
    def __init__(
        self,
        stdscr,
        char_dev_filename: str,
        pcie_stats: PcieStatsResult,
        cmd_queue: queue.Queue,
        resp_queue: queue.Queue,
    ):
        self.stdscr = stdscr
        self.cmd_queue = cmd_queue
        self.resp_queue = resp_queue

        curses.noecho()
        curses.cbreak()
        self.stdscr.keypad(1)

        curses.init_color(255, 0, 0, 0)
        curses.init_pair(1, curses.COLOR_GREEN, 255)
        curses.init_pair(2, curses.COLOR_WHITE, 255)
        curses.init_pair(3, curses.COLOR_WHITE, curses.COLOR_MAGENTA)
        curses.init_pair(4, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(5, curses.COLOR_BLACK, curses.COLOR_YELLOW)
        curses.init_pair(6, curses.COLOR_WHITE, curses.COLOR_BLUE)

        h, w = self.stdscr.getmaxyx()

        s = "Unofficial Pikes Peak/Storey Peak PCIe tester"
        self.stdscr.addstr(
            1,
            w // 2 - len(s) // 2,
            s,
            curses.A_BOLD | curses.color_pair(3),
        )

        s = "Interface #0"
        self.stdscr.addstr(3, w // 4 - len(s) // 2, s, curses.A_BOLD)

        s = "PCIe lanes 0 - 7"
        self.stdscr.addstr(4, w // 4 - len(s) // 2, s)

        for posy in range(3, 25):
            self.stdscr.addstr(posy, w // 2, "|")

        self.stdscr.addstr(6, 3, "Read speed:")
        self.stdscr.refresh()
        bar_max_val = int(pcie_stats.max_speed_GBps * 1000)
        self.bar_left_read = Bar(4, w // 2 - 4, 7, 2, max_val=bar_max_val)

        self.stdscr.refresh()
        self.stdscr.addstr(11, 3, "Write speed:")
        self.bar_left_write = Bar(4, w // 2 - 4, 12, 2, max_val=bar_max_val)

        self.stdscr.addstr(16, 3, "Mode:")
        self.radio = RadioList(5, 14, 17, 2)
        self.stdscr.addstr(16, 21, "Tr. size:")
        self.ts = TransferSizeSel(3, 12, 17, 20)

        self.controls = [self.radio, self.ts]
        self.controls_sel = 0
        self.controls[self.controls_sel].set_highlight(True)
        self.controls[self.controls_sel].refresh()

        self.stdscr.addstr(23, 2, f"Filename: {char_dev_filename}")
        status_str = (
            f"Link width = {pcie_stats.link_width}, speed = {pcie_stats.link_speed}"
        )
        self.stdscr.addstr(24, 2, status_str)

        if True:
            self.bar_right_read = Bar(3, w // 2 - 5, 12, w // 2 + 3, max_val=8000)
            self.stdscr.addstr(16, w // 2 + 4, "Mode:")
            radio2 = RadioList(5, 14, 17, w // 2 + 3)
            self.stdscr.addstr(16, w // 2 + 22, "Tr. size:")
            ts2 = TransferSizeSel(3, 12, 17, w // 2 + 21)
            self.controls.append(radio2)
            self.controls.append(ts2)

        self.msg_pane = MessagePane(h - 27, w - 4, 26, 2)
        self.msg_pane.set_title("Log messages")
        self.msg_pane.refresh()

    def run(self):
        dir = 1

        self.stdscr.nodelay(1)
        while True:
            try:
                char = self.stdscr.getch()
                if char == -1:
                    try:
                        resp: MsgResp = self.resp_queue.get_nowait()
                        self.bar_left_read.set_value(resp.read_throughput)
                        self.bar_left_write.set_value(resp.write_throughput)
                        dt_str = datetime.datetime.now().strftime(
                            "%Y-%m-%d %H:%M:%S.%f"
                        )
                        self.msg_pane.append_msg(f"[{dt_str}] {resp.msg}")
                    except queue.Empty:
                        pass
                    time.sleep(0.01)
                elif (
                    char == curses.KEY_RIGHT
                    and self.controls_sel < len(self.controls) - 1
                ):
                    self.controls[self.controls_sel].set_highlight(False)
                    self.controls[self.controls_sel].refresh()
                    self.controls_sel += 1
                    self.controls[self.controls_sel].set_highlight(True)
                    self.controls[self.controls_sel].refresh()
                elif char == curses.KEY_LEFT and self.controls_sel > 0:
                    self.controls[self.controls_sel].set_highlight(False)
                    self.controls[self.controls_sel].refresh()
                    self.controls_sel -= 1
                    self.controls[self.controls_sel].set_highlight(True)
                    self.controls[self.controls_sel].refresh()
                elif char in (
                    curses.KEY_UP,
                    curses.KEY_DOWN,
                    curses.KEY_ENTER,
                    ord("\n"),
                ):
                    self.controls[self.controls_sel].cmd(char)
                    self.controls[self.controls_sel].refresh()
                    mode = Mode(self.radio.sel)
                    self.cmd_queue.put(MsgCmd(False, self.ts.size, mode))
            except KeyboardInterrupt:
                self.cmd_queue.put(MsgCmd(True, None, None))
                break
