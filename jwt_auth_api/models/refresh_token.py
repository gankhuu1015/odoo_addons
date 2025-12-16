from odoo import models, fields


class TokenModel(models.Model):
    _name = 'jwt.refresh_token'
    _description = 'JWT Refresh Token'

    is_revoked = fields.Boolean(indexed=True)
    stored_token = fields.Char(required=True)
    user_id = fields.Many2one('res.users', required=True, ondelete='cascade')
