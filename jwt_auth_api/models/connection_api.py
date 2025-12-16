# -*- coding:utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

class ConnectionApi(models.Model):
    _name = 'connection.api'
    _description = 'Connection Rest Api'
    _rec_name = 'model_id'

    model_id = fields.Many2one('ir.model', string="Model", domain="[('transient', '=', False)]", help="Select model which can be accessed by " "REST api requests.")
    is_get = fields.Boolean(string='GET', help="Select this to enable GET method " "while sending requests.")
    is_post = fields.Boolean(string='POST', help="Select this to enable POST method" "while sending requests.")
    is_put = fields.Boolean(string='PUT', help="Select this to enable PUT method " "while sending requests.")
    is_delete = fields.Boolean(string='DELETE', help="Select this to enable DELETE method " "while sending requests.")
    
    _sql_constraints = [
        ('connection_api_unique_model',
         'unique(model_id)',
         'This model is already registered in Connection API!')
    ]

    @api.constrains('model_id')
    def _check_model_name(self):
        for rec in self:
            if not rec.model_id:
                continue
            dup = self.search_count([
                ('id', '!=', rec.id),
                ('model_id', '=', rec.model_id.id),
            ])
            if dup:
                raise ValidationError(
                    _("'%s' model is already registered in Connection API.")
                    % (rec.model_id.display_name,)
                )