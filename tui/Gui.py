import curses
import datetime
import queue
import time
from typing import Optional

from GuiElements import Bar, MessagePane, RadioList, TransferSizeSel
from QueueMsg import Mode, MsgCmd, MsgResp
from PcieStats import PcieStatsResult


class Gui:
    def __init__(
        self,
        stdscr,
        char_dev_filename0: Optional[str],
        pcie_stats0: Optional[PcieStatsResult],
        cmd_queue0: Optional[queue.Queue],
        resp_queue0: Optional[queue.Queue],
        char_dev_filename1: Optional[str],
        pcie_stats1: Optional[PcieStatsResult],
        cmd_queue1: Optional[queue.Queue],
        resp_queue1: Optional[queue.Queue],
    ):
        self.stdscr = stdscr
        self.cmd_queue0 = cmd_queue0
        self.resp_queue0 = resp_queue0
        self.cmd_queue1 = cmd_queue1
        self.resp_queue1 = resp_queue1

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

        for posy in range(3, 25):
            self.stdscr.addstr(posy, w // 2, "|")

        # ====================================================================
        s = "Interface #0"
        self.stdscr.addstr(3, w // 4 - len(s) // 2, s, curses.A_BOLD)

        s = "PCIe lanes 0 - 7"
        self.stdscr.addstr(4, w // 4 - len(s) // 2, s)

        self.controls = []

        if char_dev_filename0 is not None:
            self.stdscr.addstr(6, 3, "Read speed:")
            self.stdscr.refresh()
            bar_max_val = int(pcie_stats0.max_speed_GBps * 1000)
            self.bar_left_read = Bar(4, w // 2 - 4, 7, 2, max_val=bar_max_val)

            self.stdscr.refresh()
            self.stdscr.addstr(11, 3, "Write speed:")
            self.bar_left_write = Bar(4, w // 2 - 4, 12, 2, max_val=bar_max_val)

            self.stdscr.addstr(16, 3, "Mode:")
            self.radio_left = RadioList(5, 14, 17, 2)
            self.stdscr.addstr(16, 21, "Tr. size:")
            self.ts_left = TransferSizeSel(3, 12, 17, 20)

            self.controls.append(self.radio_left)
            self.controls.append(self.ts_left)

            self.stdscr.addstr(23, 2, f"Filename: {char_dev_filename0}")
            status_str = f"Link width = {pcie_stats0.link_width}, speed = {pcie_stats0.link_speed}"
            self.stdscr.addstr(24, 2, status_str)

        # ====================================================================
        s = "Interface #1"
        self.stdscr.addstr(3, w // 2 + w // 4 - len(s) // 2, s, curses.A_BOLD)

        s = "PCIe lanes 8 - 15"
        self.stdscr.addstr(4, w // 2 + w // 4 - len(s) // 2, s)

        if char_dev_filename1 is not None:
            self.stdscr.addstr(6, w // 2 + 3, "Read speed:")
            self.stdscr.refresh()
            bar_max_val = int(pcie_stats1.max_speed_GBps * 1000)
            self.bar_right_read = Bar(4, w // 2 - 4, 7, w // 2 + 2, max_val=bar_max_val)

            self.stdscr.refresh()
            self.stdscr.addstr(11, w // 2 + 3, "Write speed:")
            self.bar_right_write = Bar(
                4, w // 2 - 4, 12, w // 2 + 2, max_val=bar_max_val
            )

            self.stdscr.addstr(16, w // 2 + 3, "Mode:")
            self.radio_right = RadioList(5, 14, 17, w // 2 + 2)
            self.stdscr.addstr(16, w // 2 + 21, "Tr. size:")
            self.ts_right = TransferSizeSel(3, 12, 17, w // 2 + 20)

            self.controls.append(self.radio_right)
            self.controls.append(self.ts_right)

            self.stdscr.addstr(23, w // 2 + 2, f"Filename: {char_dev_filename1}")
            status_str = f"Link width = {pcie_stats1.link_width}, speed = {pcie_stats1.link_speed}"
            self.stdscr.addstr(24, w // 2 + 2, status_str)

        # ====================================================================

        self.controls_sel = 0
        self.controls[self.controls_sel].set_highlight(True)
        self.controls[self.controls_sel].refresh()

        self.msg_pane = MessagePane(h - 27, w - 4, 26, 2)
        self.msg_pane.set_title("Log messages")
        self.msg_pane.refresh()

    def run(self):
        self.stdscr.nodelay(1)
        while True:
            try:
                char = self.stdscr.getch()
                if char == -1:
                    if self.resp_queue0 is not None:
                        try:
                            resp: MsgResp = self.resp_queue0.get_nowait()
                            self.bar_left_read.set_value(resp.read_throughput)
                            self.bar_left_write.set_value(resp.write_throughput)
                            dt_str = datetime.datetime.now().strftime(
                                "%Y-%m-%d %H:%M:%S.%f"
                            )
                            self.msg_pane.append_msg(f"[{dt_str}] if0: {resp.msg}")
                        except queue.Empty:
                            pass

                    if self.resp_queue1 is not None:
                        try:
                            resp: MsgResp = self.resp_queue1.get_nowait()
                            self.bar_right_read.set_value(resp.read_throughput)
                            self.bar_right_write.set_value(resp.write_throughput)
                            dt_str = datetime.datetime.now().strftime(
                                "%Y-%m-%d %H:%M:%S.%f"
                            )
                            self.msg_pane.append_msg(f"[{dt_str}] if1: {resp.msg}")
                        except queue.Empty:
                            pass
                    # time.sleep(0.01)
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
                    if self.cmd_queue0 is not None:
                        mode = Mode(self.radio_left.sel)
                        self.cmd_queue0.put(MsgCmd(False, self.ts_left.size, mode))
                    if self.cmd_queue1 is not None:
                        mode = Mode(self.radio_right.sel)
                        self.cmd_queue1.put(MsgCmd(False, self.ts_right.size, mode))
            except KeyboardInterrupt:
                if self.cmd_queue0 is not None:
                    self.cmd_queue0.put(MsgCmd(True, None, None))
                if self.cmd_queue1 is not None:
                    self.cmd_queue1.put(MsgCmd(True, None, None))
                break
