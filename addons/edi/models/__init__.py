"""EDI models"""

# Base model patches
from . import models

# Required by edi.document, edi.gateway, and edi.transfer
from . import edi_issues

from . import edi_attachment_audit
from . import edi_connection
from . import edi_connection_local
from . import edi_connection_mail
from . import edi_connection_sftp
from . import edi_connection_xmlrpc
from . import edi_document
from . import edi_gateway
from . import edi_record
from . import edi_synchronizer
from . import edi_transfer
from . import mail_thread

from . import edi_partner_document
from . import edi_partner_record
from . import edi_partner_tutorial
from . import edi_raw_document
from . import edi_raw_record

from . import ir_attachment
