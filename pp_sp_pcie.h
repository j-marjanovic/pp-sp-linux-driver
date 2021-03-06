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

#pragma once

#define PP_SP_IOCTL_MAGIC	(0x25)

struct pp_sp_tx_cmd_resp {
	// command
	unsigned char dir_wr_rd_n; // 1 for write, 0 for read
	uint32_t size_bytes;

	// response
	u64 duration_ns;
};

#define PP_SP_IOCTL_SET_BUFFER	_IOW(PP_SP_IOCTL_MAGIC, 1, void*)
#define PP_SP_IOCTL_GET_BUFFER	_IOR(PP_SP_IOCTL_MAGIC, 1, void*)
#define PP_SP_IOCTL_START_TX	_IOWR(PP_SP_IOCTL_MAGIC, 2, struct pp_sp_tx_cmd_resp*)

