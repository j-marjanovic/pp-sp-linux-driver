import threading
import queue
import time

from QueueMsg import MsgCmd, MsgResp


class IoThread(threading.Thread):
    def __init__(self, cmd_queue: queue.Queue, resp_queue: queue.Queue):
        self.cmd_queue = cmd_queue
        self.resp_queue = resp_queue
        super().__init__()

    def run(self):
        i = 0
        while True:
            try:
                cmd: MsgCmd = self.cmd_queue.get_nowait()
                if cmd.stop:
                    return

            except queue.Empty:
                self.resp_queue.put(
                    MsgResp(f"from thread, idx = {i}", i * 100, i * 100 + 50)
                )
                i += 1
                if i > 80:
                    i = 0
                time.sleep(0.01)
