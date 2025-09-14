{
    'name': 'Sales Profitability Report',
    'version': '18.0.1.0.0',
    'summary': 'Comprehensive sales profitability analysis with order-wise revenue, cost, and margin reports',
    'description': """
Sales Profitability Report
=========================
Advanced sales profitability analysis tool providing detailed insights into revenue, costs, and margins.

Features:
- Order-wise profitability analysis
- Interactive wizard with multiple filter options
- Revenue, cost, and margin calculations from sale order lines
- Filter by date range, product category, and customer
- Exportable to Excel for further analysis
- Printable QWeb reports for presentations
- Real-time profitability calculations

Reports Include:
- Revenue from sale order lines (price_untaxed)
- Cost calculations based on product standard costs
- Profit margins and percentages
- Summary and detailed views
    """,
    'category': 'Sales/Reporting',
    'author': 'Aurangzaib Bhatti',
    'website': '',
    'depends': ['base', 'sale', 'sale_management', 'product'],
    'external_dependencies': {
        'python': ['xlsxwriter'],
    },
    'data': [
        'security/ir.model.access.csv',
        'wizard/sales_profitability_wizard_views.xml',
        'reports/sales_profitability_report_template.xml',
        'views/menu.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}