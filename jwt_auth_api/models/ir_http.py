from multiprocessing.context import AuthenticationError

import jwt
from werkzeug.exceptions import Unauthorized

from odoo import models
from odoo.http import request
from odoo.exceptions import AccessDenied
from ..setup.jwt_token import JwtToken


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _authenticate(cls, auth_method='user'):
        req = request
        http_req = req.httprequest
        auth_token = http_req.headers.get('Authorization')
        auth_type = auth_method.original_routing.get('auth')
        if auth_type != 'jwt':
            return super(IrHttp, cls)._authenticate(auth_method)
        if not auth_token:
            raise AccessDenied('Invalid access, No token provided')
        try:
            sec_key = JwtToken.get_jwt_secret()
            payload = jwt.decode(auth_token, sec_key, algorithms=[JwtToken.JWT_ALGORITHM])
            user = req.env['res.users'].browse(payload.get('user_id'))
            if not user:
                raise AccessDenied('Invalid token')
            req.update_env(user=user)
            return True
        except jwt.ExpiredSignatureError:
            raise Unauthorized('Access token expired')
        except Exception as ex:
            raise AccessDenied('Invalid access attempt, ' + str(ex))
