from odoo import fields, models


class IrModel(models.Model):

    _inherit = 'ir.model'

    is_edi_connection = fields.Boolean(string="EDI connection Model",
                                       default=False,
                                       help="This is an EDI connection model")

    def _reflect_model_params(self, model):
        vals = super(IrModel, self)._reflect_model_params(model)
        vals['is_edi_connection'] = (
            model._name != 'edi.connection.model' and
            issubclass(type(model), self.pool['edi.connection.model'])
        )
        return vals


class EdiConnectionModel(models.AbstractModel):

    _name = 'edi.connection.model'
    _description = "EDI Connection Model"
