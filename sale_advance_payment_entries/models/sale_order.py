from odoo import models, fields, api, _
from odoo.exceptions import UserError
from markupsafe import Markup


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    advance_payment = fields.Float(
        string='Advance Payment',
        help="Advance payment amount to be collected from customer"
    )
    
    advance_journal_entry_id = fields.Many2one(
        'account.move',
        string='Advance Payment Journal Entry',
        readonly=True,
        help="Journal entry created for the advance payment"
    )
    
    advance_payment_state = fields.Selection([
        ('none', 'No Advance Payment'),
        ('pending', 'Advance Payment Pending'),
        ('recorded', 'Advance Payment Recorded'),
    ], string='Advance Payment State', default='none', readonly=True)

    @api.onchange('advance_payment')
    def _onchange_advance_payment(self):
        """Update advance payment state based on amount"""
        for order in self:
            if order.advance_payment > 0:
                if order.advance_payment_state == 'none':
                    order.advance_payment_state = 'pending'
            else:
                order.advance_payment_state = 'none'

    def action_confirm(self):
        """Override to generate advance payment journal entry"""
        result = super().action_confirm()
        
        for order in self:
            if order.advance_payment > 0 and not order.advance_journal_entry_id:
                order._create_advance_payment_entry()
        
        return result

    def _create_advance_payment_entry(self):
        """Create journal entry for advance payment"""
        self.ensure_one()
        
        if self.advance_payment <= 0:
            return
        
        # Get default accounts
        receivable_account = self.partner_id.property_account_receivable_id
        if not receivable_account:
            raise UserError(_("Please configure a receivable account for customer %s") % self.partner_id.name)
        
        # Get or create advance payment account (liability account)
        advance_account = self._get_advance_payment_account()
        
        # Get default journal
        journal = self._get_advance_payment_journal()
        
        # Prepare journal entry values
        move_vals = {
            'move_type': 'entry',
            'journal_id': journal.id,
            'partner_id': self.partner_id.id,
            'date': fields.Date.context_today(self),
            'ref': _('Advance Payment for %s') % self.name,
            'line_ids': [
                # Debit: Customer Receivable
                (0, 0, {
                    'name': _('Advance Payment - %s') % self.name,
                    'account_id': receivable_account.id,
                    'partner_id': self.partner_id.id,
                    'debit': self.advance_payment,
                    'credit': 0.0,
                }),
                # Credit: Advance Received
                (0, 0, {
                    'name': _('Advance Received - %s') % self.name,
                    'account_id': advance_account.id,
                    'partner_id': self.partner_id.id,
                    'debit': 0.0,
                    'credit': self.advance_payment,
                }),
            ],
        }
        
        # Create journal entry
        move = self.env['account.move'].create(move_vals)
        
        # Link to sales order
        self.advance_journal_entry_id = move.id
        self.advance_payment_state = 'recorded'
        
        # Post the journal entry
        move.action_post()
        
        # Log in chatter
        self.message_post(
            body=Markup(_(
                "Advance payment journal entry created: %s<br/>"
                "Amount: %s %s<br/>"
                "Entry: <a href='/web#id=%s&model=account.move&view_type=form'>%s</a>"
            ) % (
                move.name,
                self.advance_payment,
                self.currency_id.name,
                move.id,
                move.name
            )),
            subtype_xmlid='mail.mt_note'
        )

    def _get_advance_payment_account(self):
        """Get or create advance payment account (liability account)"""
        # Try to find existing advance payment account
        advance_account = self.env['account.account'].search([
            ('code', '=', '2010'),
        ], limit=1)
        
        if not advance_account:
            # Create advance payment account if it doesn't exist
            advance_account = self.env['account.account'].create({
                'name': 'Advance Payments from Customers',
                'code': '2010',
                'account_type': 'liability_current',
            })
        
        return advance_account

    def _get_advance_payment_journal(self):
        """Get journal for advance payment entries"""
        # Try to find miscellaneous journal first
        journal = self.env['account.journal'].search([
            ('type', '=', 'general'),
        ], limit=1)
        
        if not journal:
            # Fallback to any available journal
            journal = self.env['account.journal'].search([], limit=1)
        
        if not journal:
            raise UserError(_("No journal found"))
        
        return journal

    def action_view_advance_journal_entry(self):
        """Action to view the advance payment journal entry"""
        self.ensure_one()
        if not self.advance_journal_entry_id:
            return
        
        return {
            'name': _('Advance Payment Journal Entry'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': self.advance_journal_entry_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    @api.constrains('advance_payment')
    def _check_advance_payment(self):
        """Validate advance payment amount"""
        for order in self:
            if order.advance_payment < 0:
                raise UserError(_("Advance payment cannot be negative"))
            if order.advance_payment > order.amount_total:
                raise UserError(_("Advance payment cannot exceed the total order amount"))