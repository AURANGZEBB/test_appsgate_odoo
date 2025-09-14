from odoo import models, fields, api
from datetime import date


class CustomerGroup(models.Model):
    _name = 'customer.group'
    _description = 'Customer Group'

    name = fields.Char(string='Group Name', required=True)
    code = fields.Char(string='Code', required=True)
    active = fields.Boolean(string='Active', default=True)


class SaleDiscountRule(models.Model):
    _name = 'sale.discount.rule'
    _description = 'Sales Discount Rule'
    _order = 'sequence, id'

    name = fields.Char(string='Rule Name', required=True)
    sequence = fields.Integer(string='Sequence', default=10, help="Sequence for rule evaluation priority")
    active = fields.Boolean(string='Active', default=True)
    
    min_amount = fields.Float(
        string='Minimum Amount',
        required=True,
        help="Minimum order amount to apply this discount rule"
    )
    max_amount = fields.Float(
        string='Maximum Amount',
        help="Maximum order amount to apply this discount rule (leave empty for no limit)"
    )
    
    discount_percent = fields.Float(
        string='Discount Percentage',
        required=True,
        help="Discount percentage to apply (0-100)"
    )
    
    customer_group = fields.Many2one(
        'customer.group',
        string='Customer Group',
        help="Customer group this rule applies to (leave empty for all customers)"
    )
    
    valid_from = fields.Date(
        string='Valid From',
        required=True,
        default=fields.Date.context_today,
        help="Start date for rule validity"
    )
    
    valid_to = fields.Date(
        string='Valid To',
        help="End date for rule validity (leave empty for no expiration)"
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True
    )
    
    @api.constrains('min_amount', 'max_amount')
    def _check_amounts(self):
        for rule in self:
            if rule.min_amount < 0:
                raise ValueError("Minimum amount cannot be negative")
            if rule.max_amount and rule.max_amount <= rule.min_amount:
                raise ValueError("Maximum amount must be greater than minimum amount")
    
    @api.constrains('discount_percent')
    def _check_discount_percent(self):
        for rule in self:
            if rule.discount_percent < 0 or rule.discount_percent > 100:
                raise ValueError("Discount percentage must be between 0 and 100")
    
    @api.constrains('valid_from', 'valid_to')
    def _check_validity_dates(self):
        for rule in self:
            if rule.valid_to and rule.valid_from > rule.valid_to:
                raise ValueError("Valid from date must be before valid to date")
    
    def is_applicable(self, amount, customer_group=None, order_date=None):
        self.ensure_one()
        if not self.active:
            return False
            
        # Check amount range
        if amount < self.min_amount:
            return False
        if self.max_amount and amount > self.max_amount:
            return False
            
        # Check date validity
        check_date = order_date or fields.Date.context_today(self)
        if check_date < self.valid_from:
            return False
        if self.valid_to and check_date > self.valid_to:
            return False
            
        # Check customer group - rule applies to all if no customer group specified
        if self.customer_group and customer_group:
            if customer_group != self.customer_group:
                return False
        
        return True
    
    def calculate_discount(self, amount):
        self.ensure_one()
        return amount * (self.discount_percent / 100)
    
    @api.model
    def find_applicable_rules(self, amount, customer_group=None, order_date=None):
        """Find all applicable discount rules and return the one with highest discount"""
        domain = [('active', '=', True)]
        rules = self.search(domain)
        
        applicable_rules = []
        for rule in rules:
            if rule.is_applicable(amount, customer_group, order_date):
                discount_amount = rule.calculate_discount(amount)
                applicable_rules.append((rule, discount_amount))
        
        if not applicable_rules:
            return self.browse()
        
        # Return the rule with the highest discount amount
        best_rule = max(applicable_rules, key=lambda x: x[1])
        return best_rule[0]