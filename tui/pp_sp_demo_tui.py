#! /usr/bin/env python3

import argparse
import curses
import queue

from Gui import Gui
from IoThread import IoThread
from PcieStats import PcieStats


def main(stdscr, char_dev_filename0, char_dev_filename1):
    if char_dev_filename0 is not None:
        cmd_queue0 = queue.Queue()
        resp_queue0 = queue.Queue()
        io_thread0 = IoThread(char_dev_filename0, cmd_queue0, resp_queue0)
        io_thread0.start()
        pcie_stats0 = PcieStats.get_stats(char_dev_filename0)
    else:
        cmd_queue0 = None
        resp_queue0 = None
        pcie_stats0 = None

    if char_dev_filename1 is not None:
        cmd_queue1 = queue.Queue()
        resp_queue1 = queue.Queue()
        io_thread1 = IoThread(char_dev_filename1, cmd_queue1, resp_queue1)
        io_thread1.start()
        pcie_stats1 = PcieStats.get_stats(char_dev_filename1)
    else:
        cmd_queue1 = None
        resp_queue1 = None
        pcie_stats1 = None

    gui = Gui(
        stdscr,
        char_dev_filename0,
        pcie_stats0,
        cmd_queue0,
        resp_queue0,
        char_dev_filename1,
        pcie_stats1,
        cmd_queue1,
        resp_queue1,
    )
    gui.run()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="")
    parser.add_argument(
        "char_dev0",
        type=str,
        help="dev filename (e.g. /dev/pp_sp_pcie_user_0000:04:00.0)",
    )

    parser.add_argument(
        "char_dev1",
        type=str,
        default="None",
        nargs="?",
        help="dev filename (e.g. /dev/pp_sp_pcie_user_0000:05:00.0)",
    )

    args = parser.parse_args()
    char_dev0 = None if args.char_dev0 == "None" else args.char_dev0
    char_dev1 = None if args.char_dev1 == "None" else args.char_dev1

    curses.wrapper(main, char_dev0, char_dev1)
