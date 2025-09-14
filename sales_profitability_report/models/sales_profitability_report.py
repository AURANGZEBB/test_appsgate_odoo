from odoo import models, fields, api


class SalesProfitabilityReport(models.AbstractModel):
    _name = 'report.sales_profitability_report.profitability_report_template'
    _description = 'Sales Profitability Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        """Get report values for QWeb template"""
        if not data:
            data = {}
        
        # If data is passed from wizard, use it
        if data.get('orders'):
            return data
        
        # Otherwise, generate default report (all orders from current month)
        wizard_model = self.env['sales.profitability.wizard']
        wizard = wizard_model.create({
            'date_from': fields.Date.today().replace(day=1),
            'date_to': fields.Date.today(),
        })
        
        return wizard._get_report_data()

    def _get_currency_symbol(self, currency_id):
        """Get currency symbol for display"""
        if currency_id:
            return currency_id.symbol or currency_id.name
        return '$'