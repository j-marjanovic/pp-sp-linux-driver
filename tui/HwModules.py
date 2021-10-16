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
    ADDR_STATUS = 0x10
    ADDR_CTRL = 0x14
    ADDR_SAMPLES = 0x20
    ADDR_SAMPLES_TX = 0x24

    def __init__(self, mem, offs):
        super().__init__(mem, offs)
        id_reg = self._rd32(self.ADDR_ID_REG)
        version = self._rd32(self.ADDR_VERSION)

    def start(self, nr_samp):
        self._wr32(self.ADDR_SAMPLES, nr_samp)
        self._wr32(self.ADDR_CTRL, 1)

    def get_state(self):
        state = self._rd32(self.ADDR_STATUS) & 1
        samp_tx = self._rd32(self.ADDR_SAMPLES_TX)
        return (state, samp_tx)


class AvalonStCheck(_Module):
    ADDR_ID_REG = 0
    ADDR_VERSION = 4
    ADDR_SAMP_TOT = 0x10
    ADDR_SAMP_OK = 0x14

    def __init__(self, mem, offs):
        super().__init__(mem, offs)
        id_reg = self._rd32(self.ADDR_ID_REG)
        version = self._rd32(self.ADDR_VERSION)

    def get_stats(self):
        tot = self._rd32(self.ADDR_SAMP_TOT)
        ok = self._rd32(self.ADDR_SAMP_OK)
        return (tot, ok)

    def clear(self):
        self._wr32(self.ADDR_SAMP_TOT, 1)


class pp_sp_tx_cmd_resp(ctypes.Structure):
    _fields_ = [
        ("dir_wr_rd_n", ctypes.c_char),
        ("size_bytes", ctypes.c_uint32),
        ("duration_ns", ctypes.c_uint64),
    ]


assert ctypes.sizeof(pp_sp_tx_cmd_resp) == pp_sp_tx_cmd_resp_size
