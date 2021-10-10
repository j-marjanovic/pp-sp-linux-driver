#! /usr/bin/env python3


import curses
import queue

from Gui import Gui
from IoThread import IoThread


def main(stdscr):
    cmd_queue = queue.Queue()
    resp_queue = queue.Queue()

    io_thread = IoThread(cmd_queue, resp_queue)
    io_thread.start()

    gui = Gui(stdscr, cmd_queue, resp_queue)
    gui.run()


if __name__ == "__main__":
    curses.wrapper(main)
