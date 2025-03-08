# -*- coding: utf-8 -*-

from num2words import num2words
from collections import defaultdict
from contextlib import ExitStack, contextmanager
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from hashlib import sha256
from json import dumps
import re
from textwrap import shorten
from unittest.mock import patch

from odoo import api, fields, models, _, Command
from odoo.addons.base.models.decimal_precision import DecimalPrecision
from odoo.addons.account.tools import format_rf_reference
from odoo.exceptions import UserError, ValidationError, AccessError, RedirectWarning

class AccountCashFlowReport(models.AbstractModel):
    _inherit = 'account.cash.flow.report.handler'

    def _dispatch_aml_data(self, tags_ids, aml_data, layout_data, report_data):
        # Dispatch the aml_data in the correct layout_line
        # if aml_data['account_account_type'] == 'asset_receivable':
        #     self._add_report_data('advance_payments_customer', aml_data, layout_data, report_data)
        # elif aml_data['account_account_type'] == 'liability_payable':
        #     self._add_report_data('advance_payments_suppliers', aml_data, layout_data, report_data)
        if aml_data['balance'] < 0:
            if aml_data['account_tag_id'] == tags_ids['operating_main']:
                self._add_report_data('paid_operating_activities_main', aml_data, layout_data, report_data)
            elif aml_data['account_tag_id'] == tags_ids['operating_other'] or aml_data['account_account_type'] == 'liability_payable':
                self._add_report_data('paid_operating_activities_other', aml_data, layout_data, report_data)
            elif aml_data['account_tag_id'] == tags_ids['investing']:
                self._add_report_data('investing_activities_cash_out', aml_data, layout_data, report_data)
            elif aml_data['account_tag_id'] == tags_ids['financing']:
                self._add_report_data('financing_activities_cash_out', aml_data, layout_data, report_data)
            else:
                self._add_report_data('unclassified_activities_cash_out', aml_data, layout_data, report_data)
        elif aml_data['balance'] > 0:
            # if aml_data['account_tag_id'] == tags_ids['operating']:
            #     self._add_report_data('received_operating_activities', aml_data, layout_data, report_data)
            if aml_data['account_tag_id'] == tags_ids['operating_main'] or aml_data['account_account_type'] == 'asset_receivable':
                self._add_report_data('received_operating_activities_main', aml_data, layout_data, report_data)
            elif aml_data['account_tag_id'] == tags_ids['operating_other']:
                self._add_report_data('received_operating_activities_other', aml_data, layout_data, report_data)
            elif aml_data['account_tag_id'] == tags_ids['investing']:
                self._add_report_data('investing_activities_cash_in', aml_data, layout_data, report_data)
            elif aml_data['account_tag_id'] == tags_ids['financing']:
                self._add_report_data('financing_activities_cash_in', aml_data, layout_data, report_data)
            else:
                self._add_report_data('unclassified_activities_cash_in', aml_data, layout_data, report_data)

    def _get_layout_data(self):
        # Indentation of the following dict reflects the structure of the report.
        return {
            'opening_balance': {'name': _('Kas dan Setara Kas, Saldo Awal'), 'level': 0},
            'net_increase': {'name': _('Jumlah Peningkatan Bersih Kas dan Setara Kas'), 'level': 0},
                'operating_activities': {'name': _('AKTIVITAS OPERASI'), 'level': 2, 'parent_line_id': 'net_increase'},
                    # 'advance_payments_customer': {'name': _('Adavnce Payments received from customers'), 'level': 3, 'parent_line_id': 'operating_activities'},
                    'received_operating_activities': {'name': _('Penerimaan Kas dari Aktivitas Operasional'), 'level': 3, 'parent_line_id': 'operating_activities'},
                        'received_operating_activities_main': {'name': _('Penerimaan dan Penghasilan'), 'level': 4, 'parent_line_id': 'received_operating_activities'},
                        'received_operating_activities_other': {'name': _('Penerimaan Lain-Lain'), 'level': 4, 'parent_line_id': 'received_operating_activities'},
                    'expense_operating_activities': {'name': _('Pengeluaran Kas dari Aktivitas Operasional'), 'level': 3, 'parent_line_id': 'operating_activities'},
                    # 'advance_payments_suppliers': {'name': _('Advance payments made to suppliers'), 'level': 3, 'parent_line_id': 'operating_activities'},
                        'paid_operating_activities_main': {'name': _('Biaya-Biaya'), 'level': 4, 'parent_line_id': 'expense_operating_activities'},
                        'paid_operating_activities_other': {'name': _('Pengeluaran yang Belum Dibiayakan'), 'level': 4, 'parent_line_id': 'expense_operating_activities'},
                'investing_activities': {'name': _('AKTIVITAS INVESTASI'), 'level': 2, 'parent_line_id': 'net_increase'},
                    'investing_activities_cash_in': {'name': _('Penerimaan Kas dari Aktivitas Investasi'), 'level': 3, 'parent_line_id': 'investing_activities'},
                    'investing_activities_cash_out': {'name': _('Pengeluaran Kas dari Aktivitas Investasi'), 'level': 3, 'parent_line_id': 'investing_activities'},
                'financing_activities': {'name': _('AKTIVITAS PENDANAAN'), 'level': 2, 'parent_line_id': 'net_increase'},
                    'financing_activities_cash_in': {'name': _('Penerimaan Kas dari Aktivitas Pendanaan'), 'level': 3, 'parent_line_id': 'financing_activities'},
                    'financing_activities_cash_out': {'name': _('Pengeluaran Kas dari Aktivitas Pendanaan'), 'level': 3, 'parent_line_id': 'financing_activities'},
                'unclassified_activities': {'name': _('Cash flows from unclassified activities'), 'level': 2, 'parent_line_id': 'net_increase'},
                    'unclassified_activities_cash_in': {'name': _('Cash in'), 'level': 3, 'parent_line_id': 'unclassified_activities'},
                    'unclassified_activities_cash_out': {'name': _('Cash out'), 'level': 3, 'parent_line_id': 'unclassified_activities'},
            'closing_balance': {'name': _('Kas dan Setara Kas, Saldo Akhir'), 'level': 0},
        }

    def _get_report_data(self, report, options, layout_data):
        report_data = {}

        currency_table_query = self.env['res.currency']._get_query_currency_table(options)

        payment_move_ids, payment_account_ids = self._get_liquidity_move_ids(report, options)

        # Compute 'Cash and cash equivalents, beginning of period'
        for aml_data in self._compute_liquidity_balance(report, options, currency_table_query, payment_account_ids, 'to_beginning_of_period'):
            self._add_report_data('opening_balance', aml_data, layout_data, report_data)
            self._add_report_data('closing_balance', aml_data, layout_data, report_data)

        # Compute 'Cash and cash equivalents, closing balance'
        for aml_data in self._compute_liquidity_balance(report, options, currency_table_query, payment_account_ids, 'strict_range'):
            self._add_report_data('closing_balance', aml_data, layout_data, report_data)

        tags_ids = {
            'operating': self.env.ref('account.account_tag_operating').id,
            'operating_main': self.env.ref('vsh_edufarm_cf.account_tag_operating_main').id,
            'operating_other': self.env.ref('vsh_edufarm_cf.account_tag_operating_other').id,
            'investing': self.env.ref('account.account_tag_investing').id,
            'financing': self.env.ref('account.account_tag_financing').id,
        }

        # Process liquidity moves
        for aml_groupby_account in self._get_liquidity_moves(report, options, currency_table_query, payment_account_ids, payment_move_ids, tags_ids.values()):
            for aml_data in aml_groupby_account.values():
                self._dispatch_aml_data(tags_ids, aml_data, layout_data, report_data)

        # Process reconciled moves
        for aml_groupby_account in self._get_reconciled_moves(report, options, currency_table_query, payment_account_ids, payment_move_ids, tags_ids.values()):
            for aml_data in aml_groupby_account.values():
                self._dispatch_aml_data(tags_ids, aml_data, layout_data, report_data)

        return report_data