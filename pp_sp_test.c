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
#include <getopt.h>
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

void ast_gen_init(void* mem_gen, uint32_t nr_samp)
{
    uint32_t id_reg = *(uint32_t*)mem_gen;
    printf("[gen] id reg = %x\n", id_reg);

    *(uint32_t*)(mem_gen + 0x20) = nr_samp;
    *(uint32_t*)(mem_gen + 0x14) = 1;
}

void ast_gen_state(void* mem_gen, uint32_t* nr_samp_gen)
{
    uint32_t state = *(uint32_t*)(mem_gen + 0x10);
    uint32_t nr_samp = *(uint32_t*)(mem_gen + 0x24);
    printf("[gen] state = %x\n", state);
    printf("[gen] nr samp = %x\n", nr_samp);
    if (nr_samp_gen) {
        *nr_samp_gen = nr_samp;
    }
}

void ast_check_clear(void* mem_check)
{
    uint32_t id_reg = *(uint32_t*)mem_check;
    printf("[check] id reg = %x\n", id_reg);

    *(uint32_t*)(mem_check + 0x10) = 1;
}

int ast_check(void* mem_check)
{

    uint32_t samp_tot = *(uint32_t*)(mem_check + 0x10);
    uint32_t samp_ok = *(uint32_t*)(mem_check + 0x14);
    printf("[check] samp = %x / %x\n", samp_ok, samp_tot);

    return (samp_ok == samp_tot);
}

void print_usage(const char* prog_name)
{
    printf("Usage: %s --dev DEV [--write] [--read]\n", prog_name);
    printf("\n");
    printf("Perform DMA transfers using the DMA engine in PP/SP FPGA\n");
    printf("\n");
    printf("options:\n");
    printf("  --help      print these help and exit\n");
    printf("  --dev       char device (e.g. /dev/pp_sp_pcie...)\n");
    printf("  --write     card to host (DMA write) transfer\n");
    printf("  --read      host to card (DMA read) transfer\n");
    printf("  --nr_samp   number of samples (32-byte words to transfer (default 64)\n");
    printf("  --count     count of loops to perform the reads and/or writes (default 1)\n");
    printf("  --msleep    sleep (in milliseconds) during each loop (default 0)\n");
}

int main(int argc, char* argv[])
{

    int nr_samp = 64;
    int count = 1;
    int loop_msleep = 0;
    char* dev = NULL;

    int c2h, h2c;

    // clang-format off
    struct option long_options[] = {
        { "help",    no_argument,       0,    'h' },
        { "dev",     required_argument, 0,    'd' },
        { "write",   no_argument,       &c2h, 1   },
        { "read",    no_argument,       &h2c, 1   },
        { "nr_samp", required_argument, 0,    'n' },
        { "count",   required_argument, 0,    'c' },
        { "msleep",  required_argument, 0,    'm' },
        { 0, 0, 0, 0 },
    };
    // clang-format on

    while (1) {
        int c = getopt_long(argc, argv, "hdwrn:", long_options, NULL);
        if (c == -1) {
            break;
        }

        switch (c) {
        case 'd':
            dev = optarg;
            break;
        case 'n':
            nr_samp = atoi(optarg);
            break;
        case 'c':
            count = atoi(optarg);
            break;
        case 'm':
            loop_msleep = atoi(optarg);
            break;
        case 'h':
            print_usage(argv[0]);
            return EXIT_SUCCESS;
        case '?':
            print_usage(argv[0]);
            return EXIT_FAILURE;
        }
    }

    printf("Arguments:\n");
    printf("  dev = %s\n", dev);
    printf("  c2h = %d, h2c = %d\n", c2h, h2c);
    printf("  nr_samp = %d, count = %d\n", nr_samp, count);

    // init
    int fd = open(dev, O_RDWR | O_SYNC);
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

    int rc = 0;
    uint32_t nr_samp_gen;
    struct pp_sp_tx_cmd_resp tx_cmd;
    clock_t t0, t1;
    uint16_t* data = (uint16_t*)calloc(1, 128 * 1024 * 1024);

    for (int i = 0; i < count; i++) {
        printf("===================================\n");
        printf("[loop] i = %d\n", i);

        if (c2h) {
            ast_gen_init(mem_gen, nr_samp);
            ast_gen_state(mem_gen, NULL);

            // card to host DMA
            tx_cmd.dir_wr_rd_n = 1;
            tx_cmd.size_bytes = nr_samp * 32;
            t0 = clock();
            rc = ioctl(fd, PP_SP_IOCTL_START_TX, &tx_cmd);
            t1 = clock();
            printf("[c2h] DMA duration %f ms\n", (float)tx_cmd.duration_ns / 1e6);
            printf("[c2h] ioctl took %f ms\n", (float)(t1 - t0) * 1000 / CLOCKS_PER_SEC);
            assert(rc == 0);

            // check DMA data
            rc = ioctl(fd, PP_SP_IOCTL_GET_BUFFER, data);
            assert(rc == 0);

            for (unsigned int i = 32; i < tx_cmd.size_bytes / 2; i++) {
                uint16_t exp = i & 0xFFFF;
                if (data[i] != exp) {
                    printf("at %d, expected = %x, got = %x\n", i, exp, data[i]);
                    return EXIT_FAILURE;
                }
            }
            ast_gen_state(mem_gen, &nr_samp_gen);
            assert((int)nr_samp_gen == nr_samp);
        }

        if (h2c) {
            ast_check_clear(mem_check);

            // host to card DMA
            tx_cmd.dir_wr_rd_n = 0;
            tx_cmd.size_bytes = nr_samp * 32;
            t0 = clock();
            rc = ioctl(fd, PP_SP_IOCTL_START_TX, &tx_cmd);
            t1 = clock();
            printf("[h2c] DMA duration %f ms\n", (float)tx_cmd.duration_ns / 1e6);
            printf("[h2c] ioctl took %f ms\n", (float)(t1 - t0) * 1000 / CLOCKS_PER_SEC);
            assert(rc == 0);

            rc = ast_check(mem_check);
            assert(rc == 1);
        }

        struct timespec t_req = {
            .tv_sec = 0,
            .tv_nsec = loop_msleep * 1000 * 1000,
        };

        nanosleep(&t_req, NULL);
    }

    // clean-up
    munmap(mem, 4 * 1024 * 1024);
    close(fd);
    return 0;
}
