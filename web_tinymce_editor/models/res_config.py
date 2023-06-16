
from odoo import models, fields, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    is_tinymce = fields.Boolean(string="Enable Tinymce Editor")

    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        res.update(
            is_tinymce=self.env['ir.config_parameter'].sudo().get_param(
                'web_tinymce_editor.is_tinymce'),
        )
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('web_tinymce_editor.is_tinymce',
                                                         self.is_tinymce)


class Partner(models.Model):
    _inherit = 'res.partner'

    test = fields.Html(string="test")
