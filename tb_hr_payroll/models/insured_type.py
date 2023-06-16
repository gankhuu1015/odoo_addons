from odoo import _, api, fields, models


class InsuredTypes(models.Model):
    _name = "insured.type"
    _description = "Insured type"
    _inherit = ['mail.thread.cc', 'mail.activity.mixin']
    code = fields.Char(string="Code", required=True)
    name = fields.Char(string="Name", required=True)
    pension_insured = fields.Float(string="Pension/ Insured/")
    pension_ao = fields.Float(string="Pension/ AO/")
    allowance_insured = fields.Float(string="Allowance/ Insured/")
    allowance_ao = fields.Float(string="Allowance/ AO/")
    health_insured = fields.Float(string="Health/ Insured/")
    health_ao = fields.Float(string="Health/ AO/")
    unemployment_insured = fields.Float(string="Unemployment/ Insured/")
    unemployment_ao = fields.Float(string="Unemployment/ AO/")
    work_injury_insured = fields.Float(string="Work Injury Insured")
    work_injury_insured_ao = fields.Float(string="Work Injury Insured/ AO/")
    social_security_contributions_percent_insured = fields.Float(
        string="Social Security Contributions Percent/ Insured/")
    social_security_contributions_percent_ao = fields.Float(
        string="Social Security Contributions Percent/ AO/")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Approved')],
        string='Status', readonly=True, copy=False,
        default='draft', tracking=True)

    def request_approve(self):
        if self.state == 'draft':
            self.state = 'done'
        elif self.state == 'done':
            self.state = 'draft'
