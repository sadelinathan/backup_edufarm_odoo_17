# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class HrExpenseRefuseWizard(models.TransientModel):
    """ Wizard to specify reason on expense sheet refusal """

    _inherit = "hr.expense.refuse.wizard"

    def action_refuse(self):
        self.sheet_ids._do_refuse(self.reason)
        return {'type': 'ir.actions.act_window_close'}

    def action_reject_custom(self):
        """
        Fungsi untuk mereject pengajuan expense.
        Hanya user yang terdaftar di level approval saat ini yang dapat melakukan reject,
        dan semua level sebelumnya harus sudah selesai (approved).
        Jika satu approver mereject, maka pengajuan akan langsung ditandai sebagai 'reject'.
        """
        self.ensure_one()
        current_user = self.env.user
        record_id = self.env.context.get('active_id')
        expense_id = self.env['hr.expense.sheet'].browse(record_id)
        print('============================= contexnya mari lihat ===========================', record_id)

        # Ambil approval yang belum diproses (approved_status belum 'approved' atau 'rejected')
        pending_approvals = expense_id.expense_approved_ids.filtered(
            lambda approval: approval.approved_status not in ['approved', 'rejected']
        )
        if not pending_approvals:
            raise UserError("Semua approval telah diproses, tidak ada yang perlu direject.")

        # Tentukan level approval terkecil yang masih pending
        current_level = min(pending_approvals.mapped('level'))
        approvals_at_level = pending_approvals.filtered(lambda approval: approval.level == current_level)
        previous_levels = expense_id.expense_approved_ids.filtered(
            lambda approval: approval.level < current_level and approval.approved_status != 'approved'
        )
        if previous_levels:
            raise UserError("Approval pada level sebelumnya belum selesai. Anda tidak dapat mereject pada level ini.")

        # Validasi: Pastikan user saat ini termasuk dalam daftar approval pada level tersebut
        user_approval = approvals_at_level.filtered(lambda approval: approval.user_id == current_user)
        if not user_approval:
            raise UserError("Anda tidak memiliki hak untuk mereject pada level ini.")

        # Update record approval user saat ini menjadi rejected
        user_approval.write({
            'approved_status': 'rejected',
            'approval_date': fields.Datetime.now(),
            'status': False,
        })

        user_created = expense_id.create_uid
        template = self.env.ref('expense_approval.email_template_hr_expense_reject')
        template.send_mail(expense_id.id, force_send=True, email_values={'email_to': user_created.login})


        # Tandai pengajuan expense sebagai rejected
        self.action_refuse()
