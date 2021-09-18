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

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <sys/mman.h>
#include <sys/ioctl.h>
#include <assert.h>
#include <unistd.h>

#include "pp_sp_pcie.h"


int main(int argc, char* argv[]) {

	if (argc != 3) {
		printf("Usage: %s DEV_FILE CMD\n", argv[0]);
		return EXIT_FAILURE;
	}

	int fd = open(argv[1], O_RDWR | O_SYNC);
	if (fd < 0) {
		perror("open()");
		return EXIT_FAILURE;
	}

	uint16_t *data = (uint16_t*)calloc(1, 4*1024*1024);
	uint64_t sum = 0;

	switch (argv[2][0]) {
	case 'g':
		printf("command: get\n");
		fd = ioctl(fd, PP_SP_IOCTL_GET_BUFFER, data);
		assert(fd == 0);
		for (int i = 0; i < 2*1024*1024; i++) {
			sum += data[i];
		}
		printf("sum = %ld (%lx)\n", sum, sum);
		break;
	case 's':
		printf("command: set\n");
		fd = ioctl(fd, PP_SP_IOCTL_SET_BUFFER, data);
		assert(fd == 0);
		break;
	case 't':
		printf("command: tx\n");
		fd = ioctl(fd, PP_SP_IOCTL_START_TX);
		assert(fd == 0);
		break;
	default:
		printf("unkown command: %s\n", argv[2]);
		break;
	}

	close(fd);
	return 0;
}
