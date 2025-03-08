# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models
from odoo.addons.base.models.res_partner import WARNING_MESSAGE, WARNING_HELP
from odoo.exceptions import UserError, ValidationError


class HrexpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"
    _description = 'Expense Approval'

    user_approval_id = fields.Many2one('user.approval', string='Approval User', ondelete='cascade', index=True, copy=False)
    expense_approved_ids = fields.One2many('hr.expense.approved', 'expense_id', string='Approval Line', ondelete='cascade', copy=False)
    submited_date = fields.Datetime(string="Submited Date", readonly=True)
    dibayar_kepada = fields.Char(string="Di Bayar Kepada", copy=False, index=True)
    keperluan = fields.Char(string="Keperluan", copy=False, index=True)
    tgl_jatuh_tempo = fields.Datetime(string="Tanggal Jatuh Tempo", copy=False)
    bank_account = fields.Char(string="Rekening Bank", copy=False, index=True)
    metode_pembayaran = fields.Selection([
        ('cash', 'Tunai / Cash'),
        ('cheque', 'Cek / Cheque'),
        ('others', 'Lain / Others')
    ], string="Metode Pembayaran")

    # def action_submit_sheet(self):
    #     self.write({'state': 'submit'})
    #     self.sudo().activity_update()
    def action_submit_sheet(self):
        """
        Mengubah status pengajuan ke 'submit' dan membuat daftar approval berdasarkan master data.
        """
        # Ambil total expense dari pengajuan
        total_expense = sum(self.expense_line_ids.mapped('total_amount'))

        # Cari master approval untuk tipe 'expense'
        approval_records = self.env['user.approval'].search([('approve_type', '=', 'expense')], limit=1)

        if not approval_records:
            raise UserError("Master approval untuk tipe expense belum diatur.")

        # Hapus approval lama jika ada
        self.expense_approved_ids.unlink()

        # Dapatkan semua line approval yang relevan berdasarkan ambang batas
        applicable_approval_lines = approval_records.user_approval_line.filtered(
            lambda line: line.start_total <= total_expense
        )

        if not applicable_approval_lines:
            raise UserError("Tidak ditemukan konfigurasi approval untuk total expense ini.")

        # Urutkan line berdasarkan level untuk memastikan urutan persetujuan
        applicable_approval_lines = applicable_approval_lines.sorted(key=lambda l: l.level)

        # Buat daftar approval baru berdasarkan semua line yang cocok
        approval_data = []
        for line in applicable_approval_lines:
            # Pastikan semua line yang memenuhi syarat (<= end_total) diproses
            # if line.start_total <= total_expense <= line.end_total:
            for user in line.user_ids:
                approval_data.append((0, 0, {
                    'name': line.name,
                    'user_id': user.id,
                    'level': line.level,
                    'expense_id': self.id,
                    'status': False,
                }))

        # Validasi jika tidak ada user yang ditemukan untuk approval
        if not approval_data:
            raise UserError("Tidak ditemukan approver yang sesuai untuk total expense ini.")

        # Tulis daftar approval ke model hr.expense.approved
        self.write({
            'expense_approved_ids': approval_data,
            'state': 'submit',
            'user_approval_id': approval_records.id,
            'submited_date': fields.Datetime.now(),
        })
        user_to_do = approval_records.user_approval_line[0]
        for x in user_to_do.user_ids:
            self._create_todo_activity(x, user_to_do.level)
        # self.sudo().activity_update()

    # def action_approve_custom(self):
    #     """
    #     Fungsi untuk menyetujui pengajuan berdasarkan urutan level.
    #     """
    #     # Pastikan hanya user yang memiliki akses bisa approve
    #     current_user = self.env.user
    #     # Temukan level dengan status belum disetujui dan user yang sama
    #     pending_approvals = self.expense_approved_ids.filtered(lambda approval: not approval.status)
    #     if not pending_approvals:
    #         raise UserError("Semua approval telah selesai atau tidak ada yang perlu disetujui.")

    #     # Cari level terkecil yang belum disetujui
    #     current_level = min(pending_approvals.mapped('level'))
    #     approvals_at_level = pending_approvals.filtered(lambda approval: approval.level == current_level)
    #     previous_levels = self.expense_approved_ids.filtered(lambda approval: approval.level < current_level and not approval.status)

    #     # Validasi: Semua level sebelumnya harus sudah selesai
    #     if previous_levels:
    #         raise UserError("Approval pada level sebelumnya belum selesai. Anda tidak dapat melanjutkan ke level ini.")

    #     # Validasi: Pastikan user saat ini adalah bagian dari level yang sedang diproses
    #     user_approval = approvals_at_level.filtered(lambda approval: approval.user_id == current_user)
    #     if not user_approval:
    #         raise UserError("Anda tidak memiliki hak untuk menyetujui pada level ini.")

    #     # Lakukan approve untuk user saat ini
    #     user_approval.write({'status': True})

    #     # Cek apakah semua user pada level ini sudah menyetujui
    #     remaining_approvals = approvals_at_level.filtered(lambda approval: not approval.status)
    #     if remaining_approvals:
    #         return  # Masih ada user lain pada level ini yang perlu approve

    #     # Jika semua user pada level ini selesai, lanjutkan ke level berikutnya
    #     next_levels = pending_approvals.filtered(lambda approval: approval.level > current_level)

    #     if not next_levels:
    #         # Jika tidak ada level berikutnya, tandai pengajuan sebagai approved
    #         self.write({'state': 'approve'})
    #         self.message_post(body="Pengajuan telah disetujui sepenuhnya.")
    #     else:
    #         # Tandai aktivitas untuk level berikutnya
    #         next_users = next_levels.mapped('user_id')
    #         self.activity_schedule(
    #             'mail.mail_activity_data_todo',
    #             user_id=next_users[0].id,  # Aktivitas ditujukan ke user pertama di level berikutnya
    #             summary=f"Approval diperlukan untuk Level {min(next_levels.mapped('level'))}"
    #         )
    def action_approve_custom(self):
        """
        Fungsi untuk menyetujui pengajuan dengan tipe persetujuan (AND/OR) dan notifikasi 
        (email/activity) berdasarkan pengaturan di field user_approval_id.
        """
        current_user = self.env.user
        pending_approvals = self.expense_approved_ids.filtered(lambda approval: not approval.status)

        if not pending_approvals:
            raise UserError("Semua approval telah selesai atau tidak ada yang perlu disetujui.")

        # Cari level terkecil yang belum disetujui
        current_level = min(pending_approvals.mapped('level'))
        approvals_at_level = pending_approvals.filtered(lambda approval: approval.level == current_level)
        previous_levels = self.expense_approved_ids.filtered(lambda approval: approval.level < current_level and not approval.status)

        # Validasi: Semua level sebelumnya harus selesai
        if previous_levels:
            raise UserError("Approval pada level sebelumnya belum selesai. Anda tidak dapat melanjutkan ke level ini.")

        # Validasi: User saat ini harus termasuk dalam level yang sedang diproses
        user_approval = approvals_at_level.filtered(lambda approval: approval.user_id == current_user)
        if not user_approval:
            raise UserError("Anda tidak memiliki hak untuk menyetujui pada level ini.")

        if self.user_approval_id.condition_type == 'or':
            # Jika salah satu user approve, semua user di level ini dianggap approve
            approvals_at_level.write({
                'status': True,
                'approved_status': 'approved',
                'approval_date': fields.Datetime.now(),  # Set tanggal persetujuan untuk semua user
            })

            # Tandai aktivitas semua user di level ini sebagai selesai
            approvals_at_level.mapped('user_id').mapped('activity_ids').filtered(
                lambda act: act.res_id == self.id and act.res_model == self._name and act.summary and f"Level {current_level}" in act.summary
            ).action_done()

            # Beri pesan error jika user lain mencoba approve lagi di level ini
            if current_user not in approvals_at_level.mapped('user_id'):
                raise UserError("Approval pada level ini telah selesai oleh user lain.")

        elif self.user_approval_id.condition_type == 'and':
            # Logika AND: Hanya user yang sedang approve yang diupdate
            user_approval.write({
                'status': True,
                'approved_status': 'approved',
                'approval_date': fields.Datetime.now(),
            })

            # Cek jika semua user di level ini telah approve
            remaining_approvals = approvals_at_level.filtered(lambda approval: not approval.status)
            if remaining_approvals:
                return  # Masih ada user lain pada level ini yang perlu approve

        # Lanjutkan ke level berikutnya atau selesaikan pengajuan
        next_levels = pending_approvals.filtered(lambda approval: approval.level > current_level)

        if not next_levels:
            # Tandai pengajuan sebagai approved jika tidak ada level berikutnya
            # self.write({'state': 'approve'})
            # self.message_post(body="Pengajuan telah disetujui sepenuhnya.")
            self.check_all_approved()
        else:
            # Buat aktivitas baru untuk user di level berikutnya
            activity_id = self.activity_ids
            activity_id.action_done()
            next_users = next_levels.mapped('user_id')
            for user in next_users:
                self._create_todo_activity(user, next_levels.level)
                # if notification_type in ['email', 'both']:
                #     template = self.env.ref('your_module.email_template_approval_notification')
                #     if template:
                #         template.send_mail(self.id, force_send=True)
                # if notification_type in ['activity', 'both']:
                #     self.activity_schedule(
                #         'mail.mail_activity_data_todo',
                #         user_id=user.id,
                #         summary=f"Approval diperlukan untuk Level {min(next_levels.mapped('level'))}"
                #     )

    def _create_todo_activity(self, user, next_levels):
        # Create an activity for the next user in the approval line
        if self.user_approval_id.notification_is == 'activity':
            self.activity_schedule('mail.mail_activity_data_todo', user_id=user.id, summary=f"Approval diperlukan untuk Level {(next_levels)}")

        if self.user_approval_id.notification_is == 'email':
            template = self.env.ref('expense_approval.email_template_hr_expense_approval')
            template.send_mail(self.id, force_send=True, email_values={'email_to': user.login})

    def check_all_approved(self):
        # Cek apakah semua level persetujuan sudah selesai
        if all(line.approved_status == 'approved' for line in self.expense_approved_ids):
            activity_id = self.activity_ids
            activity_id.action_done()
            self.action_approve_expense_sheets()


class HrExpenseApproved(models.Model):
    _name = 'hr.expense.approved'
    _description = 'User approved Expense'

    name = fields.Char(string='Name', required=True, copy=False, index=True)
    expense_id = fields.Many2one('hr.expense.sheet', string='Order Reference', ondelete='cascade', index=True, copy=False)
    user_id = fields.Many2one('res.users', string='User')
    level = fields.Integer(string="Approval Level")
    status = fields.Boolean(string="Status")
    number = fields.Integer(string="Sequence")
    approval_date = fields.Datetime(string="Approved Date")
    approved_by = fields.Char(string="Approved By", copy=False,  index=True)
    approved_status = fields.Selection([('approved', 'Approved'),('rejected', 'Rejected')], string='Approved Status', store=True, readonly=True)