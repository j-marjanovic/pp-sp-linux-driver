import dataclasses
import enum


class Mode(enum.Enum):
    IDLE = 0
    WRITE = 1
    READ = 2


@dataclasses.dataclass
class MsgCmd:
    stop: bool
    size_bytes: int
    mode: Mode


@dataclasses.dataclass
class MsgResp:
    msg: str
    read_throughput: float
    write_throughput: float
