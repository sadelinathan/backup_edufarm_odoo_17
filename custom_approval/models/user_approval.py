# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.addons.base.models.res_partner import WARNING_MESSAGE, WARNING_HELP
from odoo.exceptions import UserError, ValidationError


class UserApproval(models.Model):
    _name = 'user.approval'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'User Approval'

    name = fields.Char(string='Name', required=True, copy=False, index=True)
    user_approval_line = fields.One2many('user.approval.line', 'user_approval_id', string='Approval Line', tracking=True)
    approve_type = fields.Selection([('sale', 'Sales'), ('purchase', 'Purchase'), ('invoice', 'Invoice'), ('vendor_bill', 'Vendor Bill'), ('payment', 'Payment'), ('expense', 'Expense')], string='Type', required=True, help="Type Of Approval", tracking=True)
    is_email = fields.Boolean(string='Email', default=True)
    is_activity = fields.Boolean(string='Activity', default=True)
    notification_is = fields.Selection([('email', 'Email'), ('activity', 'Activity')], string='Notification', required=True)
    condition_type = fields.Selection([('and', 'All Conditions Must Be True(AND)'), ('or', 'Any Conditions Can Be True(OR)')])

    @api.constrains('user_approval_line')
    def approval_line_level(self):
        if self.user_approval_line:
            levels = self.user_approval_line.mapped('level')
            if len(levels) != len(set(levels)):
                raise ValidationError('Levels must be different!!!')

    @api.onchange('is_activity')
    def _onchange_activity(self):
        if self.is_activity:
            self.is_email = False

    @api.onchange('is_email')
    def _onchange_is_email(self):
        if self.is_email:
            self.is_activity = False


class UserApprovalline(models.Model):
    _name = 'user.approval.line'
    _description = 'User Approval Line'

    user_approval_id = fields.Many2one('user.approval', string='Approval User', ondelete='cascade', index=True, copy=False)
    user_ids = fields.Many2many('res.users', string="Approver Users", required=True)
    name = fields.Char(string='Name', copy=False, index=True)
    level = fields.Integer(string="Level", required=True)
    start_total = fields.Float('Start Total')
    end_total = fields.Float('End Total')
    # notifikasi
