from odoo import fields, models, tools,api


class AccountAsset(models.Model):
    _inherit = 'account.asset'

    def compute_depreciation_board(self):
        for record in self:
            record.ensure_one()
            new_depreciation_moves_data = record._recompute_board()

            # Need to unlink draft move before adding new one because if we create new move before, it will cause an error
            # in the compute for the depreciable/cumulative value
            record.depreciation_move_ids.filtered(lambda mv: mv.state == 'draft').unlink()
            new_depreciation_moves = record.env['account.move'].create(new_depreciation_moves_data)
            if record.state == 'open':
                # In case of the asset is in running mode, we post in the past and set to auto post move in the future
                new_depreciation_moves._post()

            return True

    total_depreciated   = fields.Float(string='Deprectiated' , compute='_amount_depreciation', store=True)
    total_depreciation   = fields.Float(string='Total Depreciation' , compute='_amount_depreciation', store=True)

    @api.depends('depreciation_move_ids.state')
    def _amount_depreciation(self):
        for order in self:
            total_depreciated = 0
            total_depreciation = 0
            for line in order.depreciation_move_ids:
                if line.state=='posted':
                    total_depreciated += 1
                total_depreciation += 1
            order.update({
                'total_depreciated': total_depreciated,
                'total_depreciation': total_depreciation
            })