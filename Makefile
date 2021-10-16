
obj-m := pp_sp_pcie.o


KERNELDIR ?= /lib/modules/$(shell uname -r)/build

default:
	$(MAKE) -C ${KERNELDIR}  M=$(shell pwd) modules

pp_sp_test: pp_sp_test.c
	gcc -Wall -Wextra -o pp_sp_test pp_sp_test.c

clean:
	$(MAKE) -C ${KERNELDIR} M=$(shell pwd) clean
	rm -rf pp_sp_test

