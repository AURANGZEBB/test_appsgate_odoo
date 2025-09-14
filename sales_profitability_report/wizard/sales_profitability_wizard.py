from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
import io
try:
    import xlsxwriter
except ImportError:
    xlsxwriter = None


class SalesProfitabilityWizard(models.TransientModel):
    _name = 'sales.profitability.wizard'
    _description = 'Sales Profitability Report Wizard'

    date_from = fields.Date(
        string='Date From',
        required=True,
        default=lambda self: fields.Date.today().replace(day=1)
    )
    date_to = fields.Date(
        string='Date To',
        required=True,
        default=fields.Date.today
    )
    
    partner_ids = fields.Many2many(
        'res.partner',
        string='Customers',
        domain=[('is_company', '=', True), ('customer_rank', '>', 0)],
        help="Leave empty to include all customers"
    )
    
    categ_ids = fields.Many2many(
        'product.category',
        string='Product Categories',
        help="Leave empty to include all categories"
    )
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Quotation Sent'),
        ('sale', 'Sales Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled'),
    ], string='Order Status', help="Leave empty to include all statuses")
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True
    )

    def action_generate_report(self):
        """Generate the profitability report"""
        data = self._get_report_data()
        
        return {
            'type': 'ir.actions.report',
            'report_name': 'sales_profitability_report.profitability_report_template',
            'report_type': 'qweb-pdf',
            'data': data,
            'context': self.env.context,
        }

    def action_generate_excel(self):
        """Generate Excel report"""
        if not xlsxwriter:
            raise UserError(_("The xlsxwriter Python library is not installed. Please install it using: pip install xlsxwriter"))
        
        data = self._get_report_data()
        excel_file = self._generate_excel_report(data)
        
        attachment = self.env['ir.attachment'].create({
            'name': 'Sales_Profitability_Report.xlsx',
            'type': 'binary',
            'datas': base64.b64encode(excel_file),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }

    def _get_report_data(self):
        """Get profitability data for the report"""
        # Build domain for sale orders
        domain = [
            ('date_order', '>=', self.date_from),
            ('date_order', '<=', self.date_to),
            ('company_id', '=', self.company_id.id),
        ]
        
        if self.partner_ids:
            domain.append(('partner_id', 'in', self.partner_ids.ids))
        
        if self.state:
            domain.append(('state', '=', self.state))
        else:
            # Exclude cancelled orders by default
            domain.append(('state', '!=', 'cancel'))
        
        # Get sale orders
        sale_orders = self.env['sale.order'].search(domain, order='date_order desc')
        
        report_data = []
        total_revenue = 0.0
        total_cost = 0.0
        
        for order in sale_orders:
            order_lines = order.order_line
            
            # Filter by category if specified
            if self.categ_ids:
                order_lines = order_lines.filtered(
                    lambda line: line.product_id.categ_id in self.categ_ids
                )
            
            if not order_lines:
                continue
            
            # Calculate order totals
            order_revenue = sum(line.price_subtotal for line in order_lines)
            order_cost = sum(line.product_uom_qty * line.product_id.standard_price for line in order_lines)
            order_margin = order_revenue - order_cost
            order_margin_percent = (order_margin / order_revenue * 100) if order_revenue else 0.0
            
            total_revenue += order_revenue
            total_cost += order_cost
            
            report_data.append({
                'order': order,
                'order_name': order.name,
                'order_date': order.date_order,
                'customer': order.partner_id.name,
                'revenue': order_revenue,
                'cost': order_cost,
                'margin': order_margin,
                'margin_percent': order_margin_percent,
                'lines': self._get_order_lines_data(order_lines),
            })
        
        total_margin = total_revenue - total_cost
        total_margin_percent = (total_margin / total_revenue * 100) if total_revenue else 0.0
        
        return {
            'wizard': self,
            'orders': report_data,
            'total_revenue': total_revenue,
            'total_cost': total_cost,
            'total_margin': total_margin,
            'total_margin_percent': total_margin_percent,
            'currency': self.company_id.currency_id,
        }

    def _get_order_lines_data(self, order_lines):
        """Get detailed line data for each order"""
        lines_data = []
        for line in order_lines:
            line_cost = line.product_uom_qty * line.product_id.standard_price
            line_margin = line.price_subtotal - line_cost
            line_margin_percent = (line_margin / line.price_subtotal * 100) if line.price_subtotal else 0.0
            
            lines_data.append({
                'product': line.product_id.name,
                'category': line.product_id.categ_id.name,
                'quantity': line.product_uom_qty,
                'unit_price': line.price_unit,
                'revenue': line.price_subtotal,
                'cost': line_cost,
                'margin': line_margin,
                'margin_percent': line_margin_percent,
            })
        
        return lines_data

    def _generate_excel_report(self, data):
        """Generate Excel file with profitability data"""
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        
        # Create formats
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#D7E4BC',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter'
        })
        
        currency_format = workbook.add_format({
            'num_format': '#,##0.00',
            'border': 1
        })
        
        percentage_format = workbook.add_format({
            'num_format': '0.00%',
            'border': 1
        })
        
        regular_format = workbook.add_format({'border': 1})
        
        # Create worksheet
        worksheet = workbook.add_worksheet('Sales Profitability Report')
        
        # Write headers
        headers = [
            'Order', 'Date', 'Customer', 'Revenue', 'Cost', 'Margin', 'Margin %'
        ]
        
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)
        
        # Write data
        row = 1
        for order_data in data['orders']:
            worksheet.write(row, 0, order_data['order_name'], regular_format)
            worksheet.write(row, 1, order_data['order_date'].strftime('%Y-%m-%d'), regular_format)
            worksheet.write(row, 2, order_data['customer'], regular_format)
            worksheet.write(row, 3, order_data['revenue'], currency_format)
            worksheet.write(row, 4, order_data['cost'], currency_format)
            worksheet.write(row, 5, order_data['margin'], currency_format)
            worksheet.write(row, 6, order_data['margin_percent'] / 100, percentage_format)
            row += 1
        
        # Write totals
        worksheet.write(row + 1, 2, 'TOTAL:', header_format)
        worksheet.write(row + 1, 3, data['total_revenue'], currency_format)
        worksheet.write(row + 1, 4, data['total_cost'], currency_format)
        worksheet.write(row + 1, 5, data['total_margin'], currency_format)
        worksheet.write(row + 1, 6, data['total_margin_percent'] / 100, percentage_format)
        
        # Adjust column widths
        worksheet.set_column('A:A', 15)  # Order
        worksheet.set_column('B:B', 12)  # Date
        worksheet.set_column('C:C', 25)  # Customer
        worksheet.set_column('D:G', 12)  # Amounts
        
        workbook.close()
        output.seek(0)
        return output.read()