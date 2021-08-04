"""EDI sale_stock move request records"""

from odoo import api, models, _


class EdiStockCancellationDocument(models.AbstractModel):
    _inherit = "edi.document.stock.cancellation"

    @api.model
    def grouping_move_report_list(self, moves):
        """Inherit to group by sale for moves which have a linked sale"""
        sale_moves = moves.filtered(lambda move: move.sale_line_id.order_id)
        non_sale_moves = moves - sale_moves
        grouped_moves = super(EdiStockCancellationDocument, self).grouping_move_report_list(
            non_sale_moves
        )
        for _sales_order, moves_by_sale_and_picking_type in sale_moves.groupby(
            lambda move: (move.sale_line_id.order_id, move.picking_type_id)
        ):
            grouped_moves.append(moves_by_sale_and_picking_type)
        return grouped_moves


class EdiStockCancellationRecord(models.Model):
    _inherit = "edi.record.stock.cancellation"

    @api.model
    def record_values(self, moves):
        """Inherit to use values from sale for each
        cancellation record for moves which have a linked sale"""
        res = super(EdiStockCancellationRecord, self).record_values(moves)
        sale = moves.mapped("sale_line_id.order_id")
        if sale:
            res.update(
                {
                    "order_reference": sale.client_order_ref or sale.name,
                    "customer_id": sale.partner_id.id,
                }
            )
        return res
