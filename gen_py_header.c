
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <sys/types.h>

typedef uint64_t u64;
#include "pp_sp_pcie.h"

int main()
{
    FILE* fp = fopen("tui/PpSpIoctls.py", "w+");

    fprintf(fp, "import enum\n");
    fprintf(fp, "\n");
    fprintf(fp, "class PpSpIoctls(enum.IntEnum):\n");
    fprintf(fp, "    PP_SP_IOCTL_SET_BUFFER = 0x%08lx\n", PP_SP_IOCTL_SET_BUFFER);
    fprintf(fp, "    PP_SP_IOCTL_GET_BUFFER = 0x%08lx\n", PP_SP_IOCTL_GET_BUFFER);
    fprintf(fp, "    PP_SP_IOCTL_START_TX = 0x%08lx\n", PP_SP_IOCTL_START_TX);

    fprintf(fp, "\n");
    fprintf(fp, "\n");

    fprintf(fp, "pp_sp_tx_cmd_resp_size = %ld\n", sizeof(struct pp_sp_tx_cmd_resp));

    fclose(fp);
}
