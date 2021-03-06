import ctypes
import fcntl
import mmap
import os
import queue
import struct
import threading
import time

import numpy as np

from HwModules import AvalonStGen, AvalonStCheck, pp_sp_tx_cmd_resp
from PpSpIoctls import PpSpIoctls, pp_sp_tx_cmd_resp_size
from QueueMsg import Mode, MsgCmd, MsgResp


class IoThread(threading.Thread):
    def __init__(
        self, char_dev_filename: str, cmd_queue: queue.Queue, resp_queue: queue.Queue
    ):
        self.size_bytes = 1024
        self.mode = Mode.IDLE
        self.cmd_queue = cmd_queue
        self.resp_queue = resp_queue

        self.filename = char_dev_filename
        self.fd = os.open(self.filename, os.O_RDWR)
        self.mem = mmap.mmap(self.fd, 4 * 1024 * 1024)
        self.st_gen = AvalonStGen(self.mem, 0x11000)
        self.st_check = AvalonStCheck(self.mem, 0x10000)

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

                if self.mode == Mode.READ:
                    self.st_check.clear()
                elif self.mode == Mode.WRITE:
                    self.st_gen.start(self.size_bytes)
                    state, samp_tx = self.st_gen.get_state()
                    assert state == 1

                cmd_mode = 1 if self.mode == Mode.WRITE else 0
                cmd_resp = pp_sp_tx_cmd_resp(cmd_mode, self.size_bytes, 0)
                ret = fcntl.ioctl(
                    self.fd, PpSpIoctls.PP_SP_IOCTL_START_TX, bytes(cmd_resp)
                )
                ret_cmd_resp = pp_sp_tx_cmd_resp.from_buffer_copy(ret)

                throughput_mbps = (self.size_bytes / 1000 / 1000) / (
                    ret_cmd_resp.duration_ns * 1e-9
                )

                if self.mode == Mode.READ:
                    throughput_read_mbps = throughput_mbps
                    throughput_write_mbps = 0
                    samp_tot, samp_ok = self.st_check.get_stats()
                    check_percent = samp_ok / samp_tot * 100
                    msg_check = (
                        f", check = {samp_ok}/{samp_tot} ({check_percent:.2f} %)"
                    )
                elif self.mode == Mode.WRITE:
                    state, samp_tx = self.st_gen.get_state()
                    assert state == 0
                    assert samp_tx == self.size_bytes
                    throughput_read_mbps = 0
                    throughput_write_mbps = throughput_mbps

                    cmd_resp = bytearray(4 * 1024 * 1024)
                    fcntl.ioctl(
                        self.fd, PpSpIoctls.PP_SP_IOCTL_GET_BUFFER, cmd_resp, True
                    )
                    buf = np.frombuffer(cmd_resp, dtype="uint16")

                    l = self.size_bytes // 2
                    expected = np.arange(0, l, dtype="uint16")
                    BYTES_PER_SAMP = 2
                    samp_tot = l * BYTES_PER_SAMP
                    samp_ok = np.sum(buf[0:l] == expected) * BYTES_PER_SAMP

                    check_percent = samp_ok / samp_tot * 100
                    msg_check = (
                        f", check = {samp_ok}/{samp_tot} ({check_percent:.2f} %)"
                    )
                else:
                    throughput_read_mbps = 0
                    throughput_write_mbps = 0
                    msg_check = ""

                duration_us = ret_cmd_resp.duration_ns / 1000
                self.resp_queue.put(
                    MsgResp(
                        f"{self.mode}, {self.size_bytes} B, {duration_us:.3f} us{msg_check}",
                        throughput_read_mbps,
                        throughput_write_mbps,
                    )
                )
                time.sleep(0.1)
