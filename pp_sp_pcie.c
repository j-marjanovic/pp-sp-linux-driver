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

#include <linux/init.h>
#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/mod_devicetable.h>
#include <linux/pci.h>
#include <linux/device.h>

#define MOD_NAME "pp_sp_pcie"

#define PCI_DEVICE_ID_STRATIXV (0x00a7)
#define PCI_SUBVENDOR_ID_SP_PP	(PCI_ANY_ID)
#define PCI_SUBDEVICE_ID_SP_PP	(PCI_ANY_ID)


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
	unsigned long mmio_base, mmio_length;
	void *bar0;
};

struct pp_sp_data pp_sp_data;


int pp_sp_probe(struct pci_dev *pdev, const struct pci_device_id *id) {
	int rc;
	struct device *dev = &pdev->dev;

	printk(KERN_DEBUG MOD_NAME ": pp_sp_probe\n");

	rc = pci_enable_device(pdev);
	if (unlikely(rc < 0)) {
		dev_err(dev, "Failed to enable the device\n");
		return rc;
	}

	pci_set_master(pdev);

	rc = pci_request_region(pdev, 0, MOD_NAME);
	if (unlikely(rc < 0)) {
		dev_err(dev, "pci_request_region failed for bar 0\n");
		goto fail_req_region;
	}

	pp_sp_data.mmio_base = pci_resource_start(pdev, 0);
        pp_sp_data.mmio_length = pci_resource_len(pdev, 0);

	pp_sp_data.bar0 = ioremap(pp_sp_data.mmio_base, pp_sp_data.mmio_length);

	return 0;

fail_req_region:
	pci_clear_master(pdev);
	pci_disable_device(pdev);
	return rc;
}

void pp_sp_remove(struct pci_dev *pdev) {
	printk(KERN_DEBUG MOD_NAME ": pp_sp_remove\n");
        iounmap(pp_sp_data.bar0);
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
