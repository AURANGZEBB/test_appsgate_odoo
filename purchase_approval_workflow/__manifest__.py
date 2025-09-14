{
    'name': 'Three-Level Purchase Approval Workflow',
    'version': '18.0.1.0.0',
    'summary': 'Advanced three-level approval workflow for purchase orders',
    'description': """
Three-Level Purchase Approval Workflow
======================================
This module provides a comprehensive approval workflow for purchase orders with:
- Three levels of approval based on purchase amounts
- Automatic routing based on amount thresholds
- Group-based access control for different approval levels
- Email notifications at each approval stage
- Enhanced purchase order states and workflow

Approval Levels:
- ≤ 5,000: Auto-approved
- 5,001 - 20,000: Level 1 approval required
- > 20,000: Level 2 approval required

States: draft → to_approve → approved_level1 → approved_level2 → purchase
    """,
    'category': 'Purchase',
    'author': 'Aurangzaib Bhatti',
    'website': '',
    'depends': ['base', 'purchase', 'mail'],
    'data': [
        'security/purchase_approval_groups.xml',
        'security/ir.model.access.csv',
        'data/mail_templates.xml',
        'views/purchase_approval_config_views.xml',
        'views/purchase_order_views.xml',
        'views/menu.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}