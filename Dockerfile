FROM unipartdigital/odoo-tester

# Packages
#
RUN dnf install -y python3-paramiko ; dnf clean all

# Prerequisite module installation (without tests)
#
RUN odoo-wrapper --without-demo=all -i project,document,product

# Add EDI modules
#
ADD addons /opt/odoo-addons

# Module tests
#
CMD ["--test-enable", "-i", "edi,edi_product"]
