import dataclasses


@dataclasses.dataclass
class PcieStatsResult:
    link_width: str
    link_speed: str
    max_speed_GBps: float
    subsystem_vendor: int
    subsystem_device: int


class PcieStats:
    @staticmethod
    def get_stats(char_dev_filename: str) -> PcieStatsResult:

        dev_addr = char_dev_filename.split("_")[-1]
        sysfs_path = f"/sys/module/pp_sp_pcie/drivers/pci:pp_sp_pcie/{dev_addr}"

        link_width_path = f"{sysfs_path}/current_link_width"
        link_width = open(link_width_path, "r").read().strip()

        link_speed_path = f"{sysfs_path}/current_link_speed"
        link_speed = open(link_speed_path, "r").read().strip()

        lane_rate_gbps = float(link_speed.split(" ")[0])
        if lane_rate_gbps == 2.5 or lane_rate_gbps == 5.0:
            lane_rate_gbps *= 8 / 10
        elif lane_rate_gbps == 8.0:
            lane_rate_gbps *= 128 / 130

        max_speed_GBps = lane_rate_gbps * int(link_width) / 8

        subsystem_vendor_path = f"{sysfs_path}/subsystem_vendor"
        subsystem_vendor = open(subsystem_vendor_path, "r").read().strip()
        subsystem_vendor = int(subsystem_vendor, 0)

        subsystem_device_path = f"{sysfs_path}/subsystem_device"
        subsystem_device = open(subsystem_device_path, "r").read().strip()
        subsystem_device = int(subsystem_device, 0)

        return PcieStatsResult(
            link_width=link_width,
            link_speed=link_speed,
            max_speed_GBps=max_speed_GBps,
            subsystem_vendor=subsystem_vendor,
            subsystem_device=subsystem_device,
        )
