FROM unipartdigital/odoo-tester:13.0

# Packages
#
RUN dnf install -y python3-paramiko python3-ply ; dnf clean all

# Prerequisite module installation (without tests)
#
RUN odoo-wrapper --without-demo=all -i project,document,product,stock,sale

# Add EDI modules
#
ADD addons /opt/odoo-addons

# Module tests
#
CMD ["--test-enable", "-i", "edi,edi_product,edi_stock,edi_sale"]
