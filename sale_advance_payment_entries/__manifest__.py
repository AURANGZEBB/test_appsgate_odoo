{
    'name': 'Custom Accounting Entries for Advance Payments',
    'version': '18.0.1.0.0',
    'summary': 'Automatic journal entries for advance payments on sales orders',
    'description': """
Custom Accounting Entries for Advance Payments
==============================================
This module provides automated accounting entries for advance payments on sales orders:

Features:
- Add advance payment field to sales orders
- Automatic journal entry generation on order confirmation
- Proper accounting entries: Debit Customer Receivable, Credit Advance Received
- Link journal entries to sales orders
- Activity logging in order chatter
- Integration with existing sales and accounting workflows

Accounting Flow:
- When a sales order is confirmed with an advance payment amount
- A manual journal entry is automatically created
- Debit: Customer Receivable (AR account)
- Credit: Advance Received (liability account)
- Entry is linked to the sales order for tracking
    """,
    'category': 'Sales/Accounting',
    'author': 'Aurangzaib Bhatti',
    'website': '',
    'depends': ['base', 'sale', 'account', 'sale_management'],
    'data': [
        'views/sale_order_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}