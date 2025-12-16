import os
import jwt
from datetime import datetime, timedelta

from odoo import tools
from odoo.exceptions import AccessDenied


file_for_secret = str(os.path.join(os.path.dirname(__file__), '.translator'))
print('secret file path = '+ file_for_secret)
class JwtToken:
    JWT_ALGORITHM = 'HS256'
    ACCESS_TOKEN_SECONDS = 3600 * 3
    REFRESH_TOKEN_SECONDS = 3600 * 3

    @classmethod
    def get_jwt_secret(cls):
        secret_key = ''
        with open(file_for_secret, "r") as f:
            secret_key = f.read().strip()
        if not secret_key:
            if tools.config.get('env') == 'dev':
                secret_key = tools.config.get('jwt_secret')
        if not secret_key:
            raise Exception('No secret key is set for tokens')
        return secret_key

    @classmethod
    def generate_token(cls, user_id, duration=0):
        if not duration:
            duration = JwtToken.ACCESS_TOKEN_SECONDS
        payload = {
            'user_id': user_id,
            'exp': datetime.utcnow() + timedelta(seconds=duration)
        }
        sec_key = cls.get_jwt_secret()
        created_token = jwt.encode(payload, sec_key, algorithm=cls.JWT_ALGORITHM)
        return created_token

    @classmethod
    def create_refresh_token(cls, req, uid):
        new_token = cls.generate_token(uid, JwtToken.REFRESH_TOKEN_SECONDS)
        refresh_model = req.env['jwt.refresh_token'].sudo()
        existing_token = refresh_model.search([('user_id', '=', uid)])
        if existing_token:
            existing_token.write({'stored_token': new_token, 'is_revoked': False})
        else:
            refresh_model.create({'stored_token': new_token, 'user_id': uid})
        req.future_response.set_cookie('refreshToken', new_token, httponly=True, secure=True, samesite='Lax')
        return new_token

    @classmethod
    def varify_refresh_token(cls, req, uid, token):
        try:
            sec_key = cls.get_jwt_secret()
            jwt.decode(token, sec_key, algorithms=[cls.JWT_ALGORITHM])
        except:
            raise AccessDenied('Refresh Token has been expired')
        tok_ob = req.env['jwt.refresh_token'].sudo().search([('user_id', '=', int(uid))])
        if not tok_ob:
            raise AccessDenied('Refresh Token is invalid')
        if tok_ob.stored_token != token:
            raise AccessDenied('Refresh Token has been changed')
        if tok_ob.is_revoked:
            raise AccessDenied('Token has been revoked => User Logged out, Please Log in again')
