odoo.define('edi.chat_manager', function (require) {
"use strict";

var chat_manager = require('mail.chat_manager');

var make_message = chat_manager.make_message;

chat_manager.make_message = function (data) {
    var msg = make_message(data);
    msg.edi_attachment_audit_ids = data.edi_attachment_audit_ids;
    return msg;
};

return chat_manager;
});
