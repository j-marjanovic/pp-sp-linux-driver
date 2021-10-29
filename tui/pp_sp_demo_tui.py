#! /usr/bin/env python3

import argparse
import curses
import queue

from Gui import Gui
from IoThread import IoThread
from PcieStats import PcieStats


def main(stdscr, char_dev_filename, char_dev_filename2):
    cmd_queue = queue.Queue()
    resp_queue = queue.Queue()
    io_thread = IoThread(char_dev_filename, cmd_queue, resp_queue)
    io_thread.start()
    pcie_stats = PcieStats.get_stats(char_dev_filename)

    if char_dev_filename2 is not None:
        cmd_queue2 = queue.Queue()
        resp_queue2 = queue.Queue()
        io_thread2 = IoThread(char_dev_filename2, cmd_queue2, resp_queue2)
        io_thread2.start()
        pcie_stats2 = PcieStats.get_stats(char_dev_filename2)
    else:
        cmd_queue2 = None
        resp_queue2 = None
        pcie_stats2 = None

    gui = Gui(
        stdscr,
        char_dev_filename,
        pcie_stats,
        cmd_queue,
        resp_queue,
        char_dev_filename2,
        pcie_stats2,
        cmd_queue2,
        resp_queue2,
    )
    gui.run()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="")
    parser.add_argument(
        "char_dev",
        type=str,
        help="dev filename (e.g. /dev/pp_sp_pcie_user_0000:04:00.0)",
    )

    parser.add_argument(
        "char_dev2",
        type=str,
        nargs="?",
        default=None,
        help="dev filename (e.g. /dev/pp_sp_pcie_user_0000:04:00.0)",
    )

    args = parser.parse_args()
    curses.wrapper(main, args.char_dev, args.char_dev2)
