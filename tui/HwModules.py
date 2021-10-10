#! /usr/bin/env python3

import ctypes
import os
import mmap
import struct
import fcntl

from PpSpIoctls import PpSpIoctls, pp_sp_tx_cmd_resp_size


class _Module:
    def __init__(self, mem, offs):
        self.mem = mem
        self.offs = offs

    def _rd32(self, addr):
        bs = self.mem[self.offs + addr : self.offs + addr + 4]
        val = struct.unpack("I", bs)[0]
        return val

    def _wr32(self, addr, data):
        bs = struct.pack("I", data)
        self.mem[self.offs + addr : self.offs + addr + 4] = bs


class AvalonStGen(_Module):
    ADDR_ID_REG = 0
    ADDR_VERSION = 4
    ADDR_CTRL = 0x14
    ADDR_SAMPLES = 0x20

    def __init__(self, mem, offs):
        super().__init__(mem, offs)
        id_reg = self._rd32(self.ADDR_ID_REG)
        version = self._rd32(self.ADDR_VERSION)
        print(f"[AvalonStGen] id reg  = {id_reg:08x}")
        print(f"[AvalonStGen] version = {version:08x}")

    def start(self, nr_samp):
        self._wr32(self.ADDR_SAMPLES, nr_samp)
        self._wr32(self.ADDR_CTRL, 1)


class pp_sp_tx_cmd_resp(ctypes.Structure):
    _fields_ = [
        ("dir_wr_rd_n", ctypes.c_char),
        ("size_bytes", ctypes.c_uint32),
        ("duration_ns", ctypes.c_uint64),
    ]


assert ctypes.sizeof(pp_sp_tx_cmd_resp) == pp_sp_tx_cmd_resp_size
