import ctypes
import fcntl
import mmap
import os
import queue
import struct
import threading
import time

from HwModules import AvalonStGen, pp_sp_tx_cmd_resp
from PpSpIoctls import PpSpIoctls, pp_sp_tx_cmd_resp_size
from QueueMsg import Mode, MsgCmd, MsgResp


class IoThread(threading.Thread):
    def __init__(self, cmd_queue: queue.Queue, resp_queue: queue.Queue):
        self.size_bytes = 1024
        self.mode = Mode.IDLE
        self.cmd_queue = cmd_queue
        self.resp_queue = resp_queue

        self.filename = "/dev/pp_sp_pcie_user_0000:04:00.0"
        self.fd = os.open(self.filename, os.O_RDWR)
        self.mem = mmap.mmap(self.fd, 4 * 1024 * 1024)
        self.st_gen = AvalonStGen(self.mem, 0x11000)

        super().__init__()

    def run(self):
        self.resp_queue.put(MsgResp("from IoThread: thread started", 0, 0))
        while True:
            try:
                cmd: MsgCmd = self.cmd_queue.get_nowait()
                if cmd.stop:
                    return

                self.mode = cmd.mode
                self.size_bytes = cmd.size_bytes

            except queue.Empty:
                if self.mode == Mode.IDLE:
                    time.sleep(0.1)
                    continue

                self.st_gen.start(self.size_bytes // 32)

                cmd_mode = 1 if self.mode == Mode.WRITE else 0
                cmd_resp = pp_sp_tx_cmd_resp(cmd_mode, self.size_bytes, 0)
                ret = fcntl.ioctl(
                    self.fd, PpSpIoctls.PP_SP_IOCTL_START_TX, bytes(cmd_resp)
                )
                ret_cmd_resp = pp_sp_tx_cmd_resp.from_buffer_copy(ret)

                throughput_mbps = (self.size_bytes / 1024 / 1024) / (
                    ret_cmd_resp.duration_ns * 1e-9
                )

                if self.mode == Mode.READ:
                    throughput_read_mbps = throughput_mbps
                    throughput_write_mbps = 0
                elif self.mode == Mode.WRITE:
                    throughput_read_mbps = 0
                    throughput_write_mbps = throughput_mbps
                else:
                    throughput_read_mbps = 0
                    throughput_write_mbps = 0

                self.resp_queue.put(
                    MsgResp(
                        f"mode = {self.mode}, size = {self.size_bytes} B, dur = {ret_cmd_resp.duration_ns / 1000:.2f} us",
                        throughput_read_mbps,
                        throughput_write_mbps,
                    )
                )
                time.sleep(0.1)
