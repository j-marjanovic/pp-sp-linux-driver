#! /usr/bin/env python3

import argparse
import curses
import queue

from Gui import Gui
from IoThread import IoThread
from PcieStats import PcieStats


def main(stdscr, char_dev_filename):
    cmd_queue = queue.Queue()
    resp_queue = queue.Queue()

    io_thread = IoThread(char_dev_filename, cmd_queue, resp_queue)
    io_thread.start()

    stats = PcieStats.get_stats(char_dev_filename)
    status_str = f"Link width = {stats.link_width}, speed = {stats.link_speed}"
    gui = Gui(stdscr, char_dev_filename, status_str, cmd_queue, resp_queue)
    gui.run()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="")
    parser.add_argument(
        "char_dev",
        type=str,
        help="dev filename (e.g. /dev/pp_sp_pcie_user_0000:04:00.0)",
    )

    args = parser.parse_args()
    curses.wrapper(main, args.char_dev)
