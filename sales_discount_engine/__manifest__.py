{
    'name': 'Dynamic Sales Discount Rules Engine',
    'version': '18.0.1.0.0',
    'summary': 'Advanced discount rules engine for sales orders',
    'description': """
Dynamic Sales Discount Rules Engine
===================================
This module provides a flexible discount rules engine that allows you to:
- Define discount rules based on minimum and maximum amounts
- Apply dynamic discounts to sales orders
- Manage complex discount scenarios

Features:
- Create discount rules with min/max amount criteria
- Automatic discount calculation on sales orders
- User-friendly interface for discount management
    """,
    'category': 'Sales',
    'author': 'Aurangzaib Bhatti',
    'website': '',
    'depends': ['base', 'sale','sale_management'],
    'data': [
        'security/ir.model.access.csv',
        'views/customer_group_views.xml',
        'views/sale_discount_rule_views.xml',
        'views/sale_order_views.xml',
        'views/menu.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}