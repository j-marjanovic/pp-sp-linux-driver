import dataclasses


@dataclasses.dataclass
class MsgCmd:
    stop: bool


@dataclasses.dataclass
class MsgResp:
    msg: str
    read_throughput: float
    write_throughput: float
