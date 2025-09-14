from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError


class PurchaseApprovalConfig(models.Model):
    _name = 'purchase.approval.config'
    _description = 'Purchase Approval Configuration'
    _rec_name = 'name'

    name = fields.Char(string='Configuration Name', required=True, default='Default Approval Configuration')
    
    auto_approve_limit = fields.Float(
        string='Auto Approve Limit', 
        default=5000.0,
        required=True,
        help="Purchase orders with amount less than or equal to this will be auto-approved"
    )
    
    level1_approve_limit = fields.Float(
        string='Level 1 Approval Limit',
        default=20000.0, 
        required=True,
        help="Purchase orders with amount less than or equal to this require Level 1 approval"
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True
    )
    
    active = fields.Boolean(string='Active', default=True)

    @api.constrains('auto_approve_limit', 'level1_approve_limit')
    def _check_approval_limits(self):
        for config in self:
            if config.auto_approve_limit >= config.level1_approve_limit:
                raise UserError(_("Auto approve limit must be less than Level 1 approval limit"))
            if config.auto_approve_limit < 0 or config.level1_approve_limit < 0:
                raise UserError(_("Approval limits cannot be negative"))

    @api.model
    def get_current_config(self, company_id=None):
        """Get the current active approval configuration"""
        if not company_id:
            company_id = self.env.company.id
        
        config = self.search([
            ('company_id', '=', company_id),
            ('active', '=', True)
        ], limit=1)
        
        if not config:
            # Create default config if none exists
            config = self.create({
                'name': 'Default Approval Configuration',
                'company_id': company_id
            })
        
        return config


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    # Override the state field to add new states
    state = fields.Selection([
        ('draft', 'RFQ'),
        ('sent', 'RFQ Sent'),
        ('to_approve', 'To Approve'),
        ('approved_level1', 'Level 1 Approved'),
        ('approved_level2', 'Level 2 Approved'), 
        ('purchase', 'Purchase Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled')
    ], string='Status', readonly=True, index=True, copy=False, default='draft', tracking=True)

    # Approval tracking fields
    approval_level_required = fields.Selection([
        ('auto', 'Auto Approved'),
        ('level1', 'Level 1 Required'),
        ('level2', 'Level 2 Required'),
    ], string='Approval Level Required', compute='_compute_approval_level', store=True)
    
    level1_approver_id = fields.Many2one('res.users', string='Level 1 Approver', readonly=True)
    level1_approval_date = fields.Datetime(string='Level 1 Approval Date', readonly=True)
    level2_approver_id = fields.Many2one('res.users', string='Level 2 Approver', readonly=True)  
    level2_approval_date = fields.Datetime(string='Level 2 Approval Date', readonly=True)

    @api.depends('amount_total', 'company_id')
    def _compute_approval_level(self):
        for order in self:
            config = self.env['purchase.approval.config'].get_current_config(order.company_id.id)
            
            if order.amount_total <= config.auto_approve_limit:
                order.approval_level_required = 'auto'
            elif order.amount_total <= config.level1_approve_limit:
                order.approval_level_required = 'level1'
            else:
                order.approval_level_required = 'level2'

    def button_confirm(self):
        for order in self:
            if order.state not in ('draft', 'sent'):
                continue
            
            config = self.env['purchase.approval.config'].get_current_config(order.company_id.id)
            
            # Determine required approval level based on configuration
            if order.amount_total <= config.auto_approve_limit:
                # Auto approve
                order.state = 'purchase'
                order._send_approval_notification('auto_approved')
            elif order.amount_total <= config.level1_approve_limit:
                # Level 1 approval required
                order.state = 'to_approve' 
                order._send_approval_notification('level1_required')
            else:
                # Level 2 approval required
                order.state = 'to_approve'
                order._send_approval_notification('level2_required')
        
        return True

    def action_approve_level1(self):
        """Level 1 approval action"""
        for order in self:
            if not self.env.user.has_group('purchase_approval_workflow.group_purchase_level1_approver'):
                raise AccessError(_("You don't have permission to approve Level 1 purchases"))
            
            if order.state != 'to_approve':
                raise UserError(_("Order must be in 'To Approve' state"))
            
            config = self.env['purchase.approval.config'].get_current_config(order.company_id.id)
            
            order.level1_approver_id = self.env.user.id
            order.level1_approval_date = fields.Datetime.now()
            
            if order.amount_total <= config.level1_approve_limit:
                # Level 1 is sufficient
                order.state = 'purchase'
                order._send_approval_notification('level1_approved_final')
            else:
                # Level 2 still required
                order.state = 'approved_level1'
                order._send_approval_notification('level1_approved_pending_level2')

    def action_approve_level2(self):
        """Level 2 approval action"""
        for order in self:
            if not self.env.user.has_group('purchase_approval_workflow.group_purchase_level2_approver'):
                raise AccessError(_("You don't have permission to approve Level 2 purchases"))
            
            if order.state not in ('to_approve', 'approved_level1'):
                raise UserError(_("Order must be in 'To Approve' or 'Level 1 Approved' state"))
            
            order.level2_approver_id = self.env.user.id
            order.level2_approval_date = fields.Datetime.now()
            order.state = 'purchase'
            order._send_approval_notification('level2_approved_final')

    def action_reject(self):
        """Reject the purchase order and send back to draft"""
        for order in self:
            if order.state not in ('to_approve', 'approved_level1'):
                raise UserError(_("Can only reject orders that are pending approval"))
            
            order.state = 'draft'
            order.level1_approver_id = False
            order.level1_approval_date = False
            order.level2_approver_id = False
            order.level2_approval_date = False
            order._send_approval_notification('rejected')

    def _send_approval_notification(self, notification_type):
        """Send email notifications based on approval stage"""
        self.ensure_one()
        
        template_mapping = {
            'level1_required': 'purchase_approval_workflow.mail_template_level1_approval_request',
            'level2_required': 'purchase_approval_workflow.mail_template_level2_approval_request', 
            'level1_approved_final': 'purchase_approval_workflow.mail_template_level1_approved',
            'level1_approved_pending_level2': 'purchase_approval_workflow.mail_template_level1_approved_pending_level2',
            'level2_approved_final': 'purchase_approval_workflow.mail_template_level2_approved',
            'auto_approved': 'purchase_approval_workflow.mail_template_auto_approved',
            'rejected': 'purchase_approval_workflow.mail_template_rejected',
        }
        
        template_id = template_mapping.get(notification_type)
        if template_id:
            try:
                template = self.env.ref(template_id)
                if template:
                    template.send_mail(self.id, force_send=True)
            except Exception:
                # Template not found, continue without sending email
                pass

    @api.model
    def get_approval_users(self, approval_level):
        """Get users who can approve at the specified level"""
        if approval_level == 'level1':
            group = self.env.ref('purchase_approval_workflow.group_purchase_level1_approver')
        elif approval_level == 'level2':
            group = self.env.ref('purchase_approval_workflow.group_purchase_level2_approver')
        else:
            return self.env['res.users']
        
        return group.users