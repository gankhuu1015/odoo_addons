# -*- coding: utf-8 -*-
from odoo import fields, api, models, _


class Example(models.Model):
    _name = 'example'
    _description = "Example widget"
    
    name = fields.Char(string="Name")
    body = fields.Html(string="Body")
    
    
    