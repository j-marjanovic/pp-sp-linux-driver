import dataclasses


@dataclasses.dataclass
class PcieStatsResult:
    link_width: str
    link_speed: str


class PcieStats:
    @staticmethod
    def get_stats(char_dev_filename: str) -> PcieStatsResult:

        dev_addr = "/dev/pp_sp_pcie_user_0000:05:00.0".split("_")[-1]
        sysfs_path = f"/sys/module/pp_sp_pcie/drivers/pci:pp_sp_pcie/{dev_addr}"

        link_width_path = f"{sysfs_path}/current_link_width"
        link_width = open(link_width_path, "r").read().strip()

        link_speed_path = f"{sysfs_path}/current_link_speed"
        link_speed = open(link_speed_path, "r").read().strip()

        return PcieStatsResult(link_width=link_width, link_speed=link_speed)
