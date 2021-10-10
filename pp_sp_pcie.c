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


#include <asm/atomic.h>
#include <linux/cdev.h>
#include <linux/init.h>
#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/mod_devicetable.h>
#include <linux/pci.h>
#include <linux/device.h>
#include <linux/delay.h>
#include <linux/ktime.h>

#include "pp_sp_pcie.h"


#define MOD_NAME "pp_sp_pcie"

#define PCI_DEVICE_ID_STRATIXV (0x00a7)
#define PCI_SUBVENDOR_ID_SP_PP	(PCI_ANY_ID)
#define PCI_SUBDEVICE_ID_SP_PP	(PCI_ANY_ID)

#define PP_SP_STRUCT_MAGIC	(0x77573a9c)

#define PP_SP_BUFFER_SIZE	(128*1024*1024)


static struct class *pp_sp_class = NULL;

int pp_sp_probe(struct pci_dev *dev, const struct pci_device_id *id);
void pp_sp_remove(struct pci_dev *dev);

static const struct pci_device_id ids[] = {
	{PCI_DEVICE_SUB(PCI_VENDOR_ID_ALTERA, PCI_DEVICE_ID_STRATIXV,
		PCI_SUBVENDOR_ID_SP_PP, PCI_SUBDEVICE_ID_SP_PP)},
	{0},
};

MODULE_DEVICE_TABLE(pci, ids);

static struct pci_driver pci_drv = {
	.name = MOD_NAME,
	.id_table = ids,
	.probe = pp_sp_probe,
	.remove = pp_sp_remove,
};

struct pp_sp_data {
	uint32_t magic;
	struct pci_dev *pdev;
	unsigned long bar0_base, bar0_length, bar2_base, bar2_length;
	void *bar0, *bar2;
	void *dma_buffer_virt;
	dma_addr_t dma_buffer_phys;
	dev_t char_region;
	struct cdev cdev;
	wait_queue_head_t irq_wq;
	int irq_flag;
	atomic_t irq_count;
};

static int pp_sp_cdev_open(struct inode *inode, struct file *filp) {
	struct pp_sp_data *data;
	pr_debug(MOD_NAME ": open\n");

	data = container_of(inode->i_cdev, struct pp_sp_data, cdev);
	filp->private_data = data;

	if (data->magic != PP_SP_STRUCT_MAGIC) {
		return -EFAULT;
	}

	return 0;
}

static long pp_sp_cdev_ioctl(struct file *filp, unsigned int cmd, unsigned long arg) {
	u64 t0, t1, td;
	u64 throughput_mbps;
	struct pp_sp_tx_cmd_resp* cmd_resp;

	struct pp_sp_data *data = filp->private_data;
	if (data->magic != PP_SP_STRUCT_MAGIC) {
		return -EFAULT;
	}

	pr_debug(MOD_NAME ": ioctl\n");

	switch (cmd) {
	case PP_SP_IOCTL_GET_BUFFER:
		copy_to_user((void*)arg, data->dma_buffer_virt, PP_SP_BUFFER_SIZE);
		break;
	case PP_SP_IOCTL_SET_BUFFER:
		copy_from_user(data->dma_buffer_virt, (void*)arg, PP_SP_BUFFER_SIZE);
		break;
	case PP_SP_IOCTL_START_TX:
		cmd_resp = (struct pp_sp_tx_cmd_resp*)arg;

		if ((cmd_resp->size_bytes & 3) || (cmd_resp->size_bytes == 0)) {
			return -EINVAL;
		}

		printk(KERN_DEBUG MOD_NAME ": transferring %d bytes\n", cmd_resp->size_bytes);
		iowrite32(data->dma_buffer_phys, data->bar2 + 0x20);
		iowrite32(data->dma_buffer_phys >> 32, data->bar2 + 0x24);
		iowrite32(cmd_resp->size_bytes, data->bar2 + 0x28);
		iowrite32(cmd_resp->dir_wr_rd_n << 31, data->bar2 + 0x2c);

		t0 = ktime_get_ns();
		iowrite32(0x1, data->bar2 + 0x14);
		data->irq_flag = 0;

		wait_event_interruptible_timeout(data->irq_wq, data->irq_flag != 0,
				msecs_to_jiffies(10000));
		// TODO: check return value from wait_...

		data->irq_flag = 0;

		t1 = ktime_get_ns();
		td = t1 - t0;
		copy_to_user(&cmd_resp->duration_ns, &td, sizeof(cmd_resp->duration_ns));
		throughput_mbps = cmd_resp->size_bytes * 1000ULL / td;
		printk(KERN_DEBUG MOD_NAME ": elapsed time = %lld us\n", td / 1000);
		printk(KERN_DEBUG MOD_NAME ": throughput = %lld MBps\n", throughput_mbps);

		break;
	default:
		return -EINVAL;
	}

	return 0;
}

int pp_sp_cdev_mmap(struct file *filp, struct vm_area_struct *vma) {
	int rc;
	unsigned long off;
	unsigned long phys;
	unsigned long vsize;
	unsigned long psize;
	struct pp_sp_data *data = (struct pp_sp_data *)filp->private_data;

	pr_debug(MOD_NAME ": mmap\n");

	off = vma->vm_pgoff << PAGE_SHIFT;
	phys = pci_resource_start(data->pdev, 0) + off;
	vsize = vma->vm_end - vma->vm_start;
	psize = pci_resource_end(data->pdev, 0) -
		pci_resource_start(data->pdev, 0) + 1 - off;

	if (vsize > psize)
		return -EINVAL;

	vma->vm_page_prot = pgprot_noncached(vma->vm_page_prot);
	vma->vm_flags |= VM_IO | VM_DONTEXPAND | VM_DONTDUMP;

	rc = io_remap_pfn_range(vma, vma->vm_start, phys >> PAGE_SHIFT,
			vsize, vma->vm_page_prot);
	if (rc)
		return -EAGAIN;

	return 0;
}

static const struct file_operations fops_user = {
	.owner = THIS_MODULE,
	.open = pp_sp_cdev_open,
	.unlocked_ioctl = pp_sp_cdev_ioctl,
	.mmap = pp_sp_cdev_mmap,
};

static irqreturn_t pp_sp_isr(int irq, void *payload) {
	struct pp_sp_data *data = (struct pp_sp_data*)payload;

	if (data->magic != PP_SP_STRUCT_MAGIC) {
		return IRQ_NONE;
	}

	iowrite32(1, data->bar2 + 0x64);
	atomic_inc(&data->irq_count);

	data->irq_flag = 1;
	wake_up(&data->irq_wq);

	return IRQ_HANDLED;
}

int pp_sp_probe(struct pci_dev *pdev, const struct pci_device_id *id) {
	int rc;
	struct pp_sp_data *data = NULL;
	struct device *dev = &pdev->dev;

	printk(KERN_DEBUG MOD_NAME ": pp_sp_probe\n");

	data = kzalloc(sizeof(struct pp_sp_data), GFP_KERNEL);
	if (IS_ERR(data)) {
		dev_err(dev, "Failed to allocate mem for internal data\n");
		return -ENOMEM;
	}
	dev_set_drvdata(dev, data);
	data->pdev = pdev;
	data->magic = PP_SP_STRUCT_MAGIC;
	atomic_set(&data->irq_count, 0);
	init_waitqueue_head(&data->irq_wq);
	data->irq_flag = 0;

	// PCIe related things
	rc = pci_enable_device(pdev);
	if (unlikely(rc < 0)) {
		dev_err(dev, "Failed to enable the device\n");
		return rc;
	}

	pci_set_master(pdev);

	rc = pci_enable_msi(pdev);
	if (unlikely(rc < 0)) {
		dev_err(dev, "pci_enable_msi failed\n");
		goto fail_req_region;
	}

	rc = request_irq(pdev->irq, &pp_sp_isr, 0, MOD_NAME, data);
	if (unlikely(rc < 0)) {
		dev_err(dev, "request_irq failed\n");
		goto fail_req_region;
	}

	rc = pci_request_region(pdev, 0, MOD_NAME);
	if (unlikely(rc < 0)) {
		dev_err(dev, "pci_request_region failed for bar 0\n");
		goto fail_req_region;
	}

	rc = pci_request_region(pdev, 2, MOD_NAME);
	if (unlikely(rc < 0)) {
		dev_err(dev, "pci_request_region failed for bar 2\n");
		goto fail_req_region;
	}

	data->bar0_base = pci_resource_start(pdev, 0);
	data->bar0_length = pci_resource_len(pdev, 0);
	data->bar0 = ioremap(data->bar0_base, data->bar0_length);

	data->bar2_base = pci_resource_start(pdev, 2);
	data->bar2_length = pci_resource_len(pdev, 2);
	data->bar2 = ioremap(data->bar2_base, data->bar2_length);

	// DMA buffer
	dma_set_coherent_mask(dev, DMA_BIT_MASK(64));
	data->dma_buffer_virt = dma_alloc_coherent(dev, PP_SP_BUFFER_SIZE,
			&data->dma_buffer_phys, GFP_KERNEL);
	printk(KERN_DEBUG MOD_NAME ": DMA buffer virt = %p\n", data->dma_buffer_virt);
	printk(KERN_DEBUG MOD_NAME ": DMA buffer phys = %llx\n", data->dma_buffer_phys);

	// char device
	rc = alloc_chrdev_region(&data->char_region, 0, 1, MOD_NAME);
	if (rc < 0) {
		dev_err(dev, "alloc_chrdev_region failed\n");
		return rc;
	}

	cdev_init(&data->cdev, &fops_user);
	rc = cdev_add(&data->cdev, data->char_region, 1);
	if (rc < 0) {
		printk(KERN_DEBUG MOD_NAME ": cdev_add failed with %d\n", rc);
		goto fail_unreg_ch_reg;
	}


	device_create(pp_sp_class, dev, data->char_region, NULL,
		MOD_NAME "_user_" "%s", pci_name(pdev));

	return 0;

fail_cdev_del:
	cdev_del(&data->cdev);

fail_unreg_ch_reg:
	unregister_chrdev_region(data->char_region, 1);

fail_req_region:
	pci_clear_master(pdev);
	pci_disable_device(pdev);
	return rc;
}

void pp_sp_remove(struct pci_dev *pdev) {
	struct pp_sp_data *data = NULL;
	printk(KERN_DEBUG MOD_NAME ": pp_sp_remove\n");

	data = (struct pp_sp_data*)dev_get_drvdata(&pdev->dev);

	free_irq(pdev->irq, data);
	printk(KERN_DEBUG MOD_NAME ": interrupt count = %u\n",
			atomic_read(&data->irq_count));

	pci_disable_msi(pdev);

	device_destroy(pp_sp_class, data->char_region);
	cdev_del(&data->cdev);

	dma_free_coherent(&pdev->dev, PP_SP_BUFFER_SIZE, data->dma_buffer_virt,
			data->dma_buffer_phys);

	iounmap(data->bar0);
	iounmap(data->bar2);
	pci_release_regions(pdev);
	pci_clear_master(pdev);
	pci_disable_device(pdev);
}

static int __init pp_sp_init(void) {
	printk(KERN_INFO MOD_NAME ": pp_sp_init\n");

	pp_sp_class = class_create(THIS_MODULE, MOD_NAME);
	if (IS_ERR(pp_sp_class)) {
		pr_err("Could not create class\n");
		return PTR_ERR(pp_sp_class);
	}

	return pci_register_driver(&pci_drv);
}

static void __exit pp_sp_exit(void) {
	printk(KERN_INFO MOD_NAME ": pp_sp_exit\n");

	pci_unregister_driver(&pci_drv);
	class_destroy(pp_sp_class);
}

module_init(pp_sp_init);
module_exit(pp_sp_exit);

MODULE_LICENSE("GPL");
MODULE_AUTHOR("Jan Marjanovic");
MODULE_DESCRIPTION("PCIe driver for Pikes Peak/Storey Peak board");
MODULE_VERSION("0.1.0");
