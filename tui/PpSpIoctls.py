import enum


class PpSpIoctls(enum.IntEnum):
    PP_SP_IOCTL_SET_BUFFER = 0x40082501
    PP_SP_IOCTL_GET_BUFFER = 0x80082501
    PP_SP_IOCTL_START_TX = 0xC0082502


pp_sp_tx_cmd_resp_size = 16
