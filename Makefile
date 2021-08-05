
obj-m := pp_sp_pcie.o


KERNELDIR ?= /lib/modules/$(shell uname -r)/build

default:
	$(MAKE) -C ${KERNELDIR}  M=$(shell pwd) modules

clean:
	$(MAKE) -C ${KERNELDIR} M=$(shell pwd) clean

