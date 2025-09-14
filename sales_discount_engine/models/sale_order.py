from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    applied_discount_rule_id = fields.Many2one(
        'sale.discount.rule',
        string='Applied Discount Rule',
        help="The discount rule that was applied to this order"
    )
    
    applied_discount_amount = fields.Float(
        string='Applied Discount Amount',
        help="Total discount amount applied to this order"
    )
    
    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        for order in orders:
            order._apply_discount_rules()
        return orders
    
    def write(self, vals):
        result = super().write(vals)
        # Reapply discounts if order lines changed
        if 'order_line' in vals:
            for order in self:
                if order.state in ['draft', 'sent']:
                    order._apply_discount_rules()
        return result
    
    def action_reapply_discount(self):
        """Button action to manually reapply discount rules"""
        for order in self:
            order._apply_discount_rules()
    
    def _apply_discount_rules(self):
        """Apply the best matching discount rule to the order"""
        self.ensure_one()
        
        if self.state not in ['draft', 'sent']:
            return
        
        # Remove existing discount lines
        discount_lines = self.order_line.filtered(lambda line: line.is_discount_line)
        discount_lines.unlink()
        
        # Reset discount tracking fields
        self.applied_discount_rule_id = False
        self.applied_discount_amount = 0.0
        
        # Calculate order total (excluding discount lines)
        order_total = sum(line.price_subtotal for line in self.order_line if not line.is_discount_line)
        
        if order_total <= 0:
            return
        
        # Find the best discount rule (no customer group filtering for now)
        best_rule = self.env['sale.discount.rule'].find_applicable_rules(
            amount=order_total,
            customer_group=None,  # Can be extended later if needed
            order_date=self.date_order.date() if self.date_order else fields.Date.context_today(self)
        )
        
        if not best_rule:
            return
        
        # Calculate discount amount
        discount_amount = best_rule.calculate_discount(order_total)
        
        if discount_amount > 0:
            # Create discount line
            discount_product = self._get_discount_product()
            if discount_product:
                discount_line_vals = {
                    'order_id': self.id,
                    'product_id': discount_product.id,
                    'name': f'Discount: {best_rule.name}',
                    'product_uom_qty': 1,
                    'price_unit': -discount_amount,
                    'is_discount_line': True,
                }
                self.env['sale.order.line'].create(discount_line_vals)
                
                # Update tracking fields
                self.applied_discount_rule_id = best_rule.id
                self.applied_discount_amount = discount_amount
    
    def _get_discount_product(self):
        """Get or create the discount product"""
        discount_product = self.env['product.product'].search([
            ('default_code', '=', 'DISCOUNT'),
            ('company_id', 'in', [self.company_id.id, False])
        ], limit=1)
        
        if not discount_product:
            # Create discount product if it doesn't exist
            discount_product = self.env['product.product'].create({
                'name': 'Discount',
                'default_code': 'DISCOUNT',
                'type': 'service',
                'invoice_policy': 'order',
                'taxes_id': [(5, 0, 0)],  # No taxes
                'supplier_taxes_id': [(5, 0, 0)],  # No taxes
                'company_id': self.company_id.id,
            })
        
        return discount_product


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    
    is_discount_line = fields.Boolean(
        string='Is Discount Line',
        default=False,
        help="Indicates if this line is an automatically applied discount"
    )