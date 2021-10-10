import dataclasses


@dataclasses.dataclass
class MsgCmd:
    stop: bool
    size_bytes: int


@dataclasses.dataclass
class MsgResp:
    msg: str
    read_throughput: float
    write_throughput: float
