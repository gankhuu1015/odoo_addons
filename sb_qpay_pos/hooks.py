from odoo import SUPERUSER_ID, api


def post_init_hook(env):
    env = api.Environment(env.cr, SUPERUSER_ID, {})
    for company in env["res.company"].sudo().search([]):
        env["pos.payment.method"].with_company(company)._sb_qpay_pos_ensure_default_method(company=company)
