/*
 * Linux driver for Pikes Peak/Storey Peak reference design
 *
 * Copyright (c) 2021 Jan Marjanovic
 *
 * This source code is free software: you can redistribute it and/or
 * modify it under the terms of the GNU General Public License, version 2
 * as published by the Free Software Foundation.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 */

#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <time.h>
#include <unistd.h>

typedef uint64_t u64;

#include "pp_sp_pcie.h"

void ast_gen_init(void* mem_gen)
{
    uint32_t id_reg = *(uint32_t*)mem_gen;
    printf("[gen] id reg = %x\n", id_reg);

    uint32_t gen_en_before = *(uint32_t*)(mem_gen + 0x14);
    *(uint32_t*)(mem_gen + 0x14) = 1;
    uint32_t gen_en_after = *(uint32_t*)(mem_gen + 0x14);
    printf("[gen] mem gen before = %x, after = %x\n", gen_en_before, gen_en_after);
}

void ast_check_clear(void* mem_check)
{
    uint32_t id_reg = *(uint32_t*)mem_check;
    printf("[check] id reg = %x\n", id_reg);

    //*(uint32_t*)(mem_gen + 0x14) = 1;
}

int main(int argc, char* argv[])
{

    // init
    if (argc != 2) {
        printf("Usage: %s DEV_FILE\n", argv[0]);
        return EXIT_FAILURE;
    }

    int fd = open(argv[1], O_RDWR | O_SYNC);
    if (fd < 0) {
        perror("open()");
        return EXIT_FAILURE;
    }

    void* mem = mmap(NULL, 4 * 1024 * 1024, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
    if (mem == MAP_FAILED) {
        perror("mmap()");
        close(fd);
        return EXIT_FAILURE;
    }

    // HW (Data Gen, Data Check) init
    void* mem_gen = mem + 0x11000;
    void* mem_check = mem + 0x10000;

    ast_gen_init(mem_gen);
    ast_check_clear(mem_check);

    // card to host DMA
    int rc;
    struct pp_sp_tx_cmd_resp tx_cmd;
    tx_cmd.dir_wr_rd_n = 1;
    tx_cmd.size_bytes = 0x1000000;
    clock_t t0, t1;
    t0 = clock();
    rc = ioctl(fd, PP_SP_IOCTL_START_TX, &tx_cmd);
    t1 = clock();
    printf("[c2h] DMA duration %f ms\n", (float)tx_cmd.duration_ns / 1e6);
    printf("[c2h] ioctl took %f ms\n", (float)(t1 - t0) * 1000 / CLOCKS_PER_SEC);
    assert(rc == 0);

    // check DMA data
    uint16_t* data = (uint16_t*)calloc(1, 128 * 1024 * 1024);
    rc = ioctl(fd, PP_SP_IOCTL_GET_BUFFER, data);
    assert(rc == 0);

    // TODO: clear skid buffer when DMA in idle
    for (unsigned int i = 32; i < 0x1000000 / 2; i++) {
        if (data[i] != ((i - 32) & 0xFFFF)) {
            printf("at %d, expected = %x, got = %x\n", i, i - 32, data[i]);
            return EXIT_FAILURE;
        }
    }

    // host to card DMA
    tx_cmd.dir_wr_rd_n = 0;
    tx_cmd.size_bytes = 0x1000000;
    t0 = clock();
    rc = ioctl(fd, PP_SP_IOCTL_START_TX, &tx_cmd);
    t1 = clock();
    printf("[h2c] DMA duration %f ms\n", (float)tx_cmd.duration_ns / 1e6);
    printf("[h2c] ioctl took %f ms\n", (float)(t1 - t0) * 1000 / CLOCKS_PER_SEC);
    assert(rc == 0);

    // clean-up
    munmap(mem, 4 * 1024 * 1024);
    close(fd);
    return 0;
}
