from odoo import http
from odoo.http import request
from ..setup.jwt_token import JwtToken
from odoo.addons.jwt_auth_api.common import valid_response, invalid_response
import logging
_logger = logging.getLogger(__name__)
import ast
import json
from datetime import datetime, date

class ApiAuth(http.Controller):

    @http.route('/api/login', type='json', auth='none', methods=['POST'], csrf="*")
    def authenticate_post(self, **kwargs):
        params = self.__class__.get_json_params()
        login = params.get('login')
        password = params.get('password')
        if not login or not password:
            return {"error": "Please provide login and password"}
        try:
            if not request.db:
                raise Exception(_("Could not select database '%s'", request.db))
            _logger.info("Select database: %s", request.db)
            credential = {'login': login, 'password': password, 'type': 'password'}
            auth = request.session.authenticate(request.env, credential)
            uid = auth.get('uid', None)
            if not uid:
                return {"error": "Invalid login or password"}
        except:
            return {"error": "Invalid login or password"}
        try:
            access_token = JwtToken.generate_token(uid)
            refresh_token = JwtToken.create_refresh_token(request, uid)
            rotation_period = JwtToken.REFRESH_TOKEN_SECONDS * 3/4
            res_data = {
                "access_token": access_token,
                "user_id": uid,
            }
            is_browser = request.httprequest.user_agent.browser
            if not is_browser:
                res_data['refreshToken'] = refresh_token
            return res_data
        except Exception as exc:
            return {"error": str(exc)}

    @http.route('/api/update/access-token', type='json', auth='none', methods=['POST'], csrf=False)
    def refresh_access_token(self, **kwargs):
        """
        Generate a new access token using a valid refresh token.
        """
        params = self.__class__.get_json_params()
        user_id = params.get('user_id')
        if not user_id:
            return {'error': 'User id not given'}
        user_id = int(user_id)
        refresh_token = self.__class__.get_refresh_token(request)
        JwtToken.varify_refresh_token(request, user_id, refresh_token)
        new_access_token = JwtToken.generate_token(user_id)
        return {'access_token': new_access_token}
    
    @http.route('/api/update/refresh-token', type='json', auth='jwt', methods=['POST'], csrf=False)
    def rotate_refresh_token(self, **kwargs):
        """
        Rotate(refresh) refresh token using the current valid refresh token.
        For browsers: set refresh token in HttpOnly cookie.
        For non-browser clients: return refresh token in JSON.
        """
        params = self.__class__.get_json_params()
        user_id = params.get('user_id')
        if not user_id:
            return {'error': 'User id not given'}
        user_id = int(user_id)
        current_refresh_token = self.__class__.get_refresh_token(request)
        JwtToken.varify_refresh_token(request, user_id, current_refresh_token)

        new_refresh_token = JwtToken.create_refresh_token(request, user_id)
        response_data = {'status': 'done'}
        is_browser_client = bool(request.httprequest.user_agent.browser)
        if is_browser_client:
            # Avoid exposing refresh token in response body for browsers
            response_data['refreshToken'] = 1
            request.future_response.set_cookie(
                'refreshToken',
                new_refresh_token,
                httponly=True,
                secure=True,
                samesite='Lax',
            )
        else:
            response_data['refreshToken'] = new_refresh_token
        return response_data


    @http.route('/api/revoke/token', type='json', auth='jwt', methods=['POST'], csrf=False)
    def revoke_tokens(self, **kwargs):
        """
        Revoke(refresh) token (logout). After this, refresh token can’t be used again.
        """
        params = self.__class__.get_json_params()
        user_id = params.get('user_id')
        if not user_id:
            return {'error': 'User id not given'}
        user_id = int(user_id)
        refresh_token = self.get_refresh_token(request)
        JwtToken.varify_refresh_token(request, user_id, refresh_token)
        refresh_token_rec = request.env['jwt.refresh_token'].sudo().search(
            [('user_id', '=', user_id)],
            limit=1
        )
        if refresh_token_rec:
            refresh_token_rec.is_revoked = True
        return {'status': 'success', 'logged_out': 1}
    
    @classmethod
    def get_refresh_token(cls, req_obj):
        key_name = 'refreshToken'
        http_req = req_obj.httprequest
        long_term_token = http_req.cookies.get(key_name)
        if not long_term_token:
            long_term_token = http_req.headers.get(key_name)
        return long_term_token

    @classmethod
    def get_json_params(cls):
        http_req = request.httprequest
        params = {}
        if hasattr(http_req, 'json'):
            params = http_req.json or {}
        if not (len(params.keys())):
            if hasattr(request, 'params'):
                params = request.params or {}
        return params
    
    @http.route(['/api/send_request'], type='http', auth='jwt', methods=['GET', 'POST', 'PUT', 'DELETE'], csrf=False)
    def fetch_data(self, **kw):
        """JWT-authenticated controller"""
        model_name = kw.get('model')
        if not model_name:
            return invalid_response("No model provided", 400)

        model_id = request.env['ir.model'].sudo().search([('model', '=', model_name)], limit=1)
        if not model_id:
            return invalid_response("Invalid model, check spelling or module installation", 400)

        rec_id = int(kw.get('id', 0))
        return self.generate_response(request.httprequest.method, model_id.id, rec_id)
    
    # ----------------------------
    # Helpers
    # ----------------------------
    def _parse_json_param(self, raw):
        if raw is None or raw == "":
            return None
        if isinstance(raw, (dict, list)):
            return raw
        if isinstance(raw, str):
            try:
                return json.loads(raw)
            except Exception:
                pass
            try:
                return ast.literal_eval(raw)
            except Exception:
                return None
        return None
    
    def _iso_convert(self, obj):
        """Convert date/datetime to isoformat inside dict/list recursively (lightweight)."""
        if isinstance(obj, dict):
            for k, v in list(obj.items()):
                if isinstance(v, (datetime, date)):
                    obj[k] = v.isoformat()
                elif isinstance(v, (dict, list)):
                    self._iso_convert(v)
        elif isinstance(obj, list):
            for i in obj:
                self._iso_convert(i)

    def _parse_domain(self, raw_domain):
        if not raw_domain:
            return []
        try:
            domain = ast.literal_eval(raw_domain)
            # "True"/"False" string засах
            for cond in domain:
                if isinstance(cond, (list, tuple)) and len(cond) >= 3:
                    if cond[2] == 'False':
                        cond[2] = False
                    elif cond[2] == 'True':
                        cond[2] = True
            return domain
        except Exception:
            return None
        
    def _expand_relations(self, model_name, records, expand_spec):
        """
        expand_spec example:
          {
            "family_ids": ["name"],
            "parent_id": ["name","phone"]
          }
        - many2one -> объект (dict) болгоно (эсвэл None)
        - x2many (one2many/many2many) -> dict list болгоно
        """
        if not expand_spec or not isinstance(expand_spec, dict) or not records:
            return records

        Model = request.env[model_name].sudo()

        for field_name, sub_fields in expand_spec.items():
            if not isinstance(sub_fields, list) or not sub_fields:
                continue

            field = Model._fields.get(field_name)
            if not field:
                continue

            if field.type not in ("many2one", "one2many", "many2many"):
                continue

            comodel = field.comodel_name

            # --- MANY2ONE: Odoo search_read returns [id, display_name] ---
            if field.type == "many2one":
                ids = set()
                for r in records:
                    val = r.get(field_name)
                    if isinstance(val, list) and len(val) >= 1 and isinstance(val[0], int):
                        ids.add(val[0])
                if not ids:
                    for r in records:
                        r[field_name] = None
                    continue
                # batch read related
                fields_to_read = ["id"] + [f for f in sub_fields if f != "id"]
                sub_recs = request.env[comodel].sudo().search_read(
                    domain=[("id", "in", list(ids))],
                    fields=fields_to_read,
                )
                for sr in sub_recs:
                    self._iso_convert(sr)

                sub_map = {sr["id"]: sr for sr in sub_recs if sr.get("id")}

                for r in records:
                    val = r.get(field_name)
                    if isinstance(val, list) and len(val) >= 1 and val[0] in sub_map:
                        r[field_name] = sub_map.get(val[0])
                    else:
                        r[field_name] = None

            # --- X2MANY: returns [ids...] ---
            else:
                all_ids = set()
                for r in records:
                    ids = r.get(field_name) or []
                    if isinstance(ids, list):
                        for i in ids:
                            if isinstance(i, int):
                                all_ids.add(i)

                if not all_ids:
                    for r in records:
                        r[field_name] = []
                    continue

                fields_to_read = ["id"] + [f for f in sub_fields if f != "id"]
                sub_recs = request.env[comodel].sudo().search_read(
                    domain=[("id", "in", list(all_ids))],
                    fields=fields_to_read,
                )
                for sr in sub_recs:
                    self._iso_convert(sr)

                sub_map = {sr["id"]: sr for sr in sub_recs if sr.get("id")}

                for r in records:
                    ids = r.get(field_name) or []
                    if isinstance(ids, list):
                        r[field_name] = [sub_map[i] for i in ids if i in sub_map]
                    else:
                        r[field_name] = []

        return records

    # ----------------------------
    # Main
    # ----------------------------
    def generate_response(self, method, model_id, rec_id):
        option = request.env['connection.api'].sudo().search([('model_id', '=', model_id)], limit=1)
        if not option:
            return invalid_response("No Record Created for the model", 400)

        model_name = option.model_id.model

        # ---------------- GET: query params ----------------
        if method == "GET":
            if not option.is_get:
                return invalid_response("Method Not Allowed", 405)

            fields = self._parse_json_param(request.params.get("fields"))
            expand = self._parse_json_param(request.params.get("expand")) or {}

            if not fields or not isinstance(fields, list):
                return invalid_response("fields must be a list. Example: fields=[\"name\"]", 400)
            if expand and not isinstance(expand, dict):
                return invalid_response("expand must be a dict. Example: expand={\"family_ids\":[\"name\"]}", 400)

            if rec_id:
                domain = [("id", "=", rec_id)]
            else:
                domain = []
                raw_domain = request.params.get("domain")
                if raw_domain:
                    parsed_domain = self._parse_domain(raw_domain)
                    if parsed_domain is None:
                        return invalid_response("Invalid format for domain parameter", 400)
                    domain = parsed_domain

            page = int(request.params.get("offset", 1))
            page_size = int(request.params.get("limit", 20))
            offset = (page - 1) * page_size

            # expand keys-ийг эхний search_read-д оруулж ирнэ (id list / [id,name] хэлбэрээр)
            read_fields = list(dict.fromkeys(fields + list(expand.keys())))

            try:
                total = request.env[model_name].sudo().search_count(domain)
                records = request.env[model_name].sudo().search_read(
                    domain=domain,
                    fields=read_fields,
                    offset=offset,
                    limit=page_size,
                    order="create_date desc"
                )

                # iso convert + expand
                for r in records:
                    self._iso_convert(r)

                records = self._expand_relations(model_name, records, expand)

                return valid_response(records, status=200, page=page, page_size=page_size, total=total)

            except Exception as e:
                _logger.exception("GET error %s: %s", model_name, str(e))
                return invalid_response(str(e), 500)

        # ---------------- POST/PUT: body ----------------
        if method in ("POST", "PUT"):
            if method == "POST" and not option.is_post:
                return invalid_response("Method Not Allowed", 405)
            if method == "PUT" and not option.is_put:
                return invalid_response("Method Not Allowed", 405)
            if method == "PUT" and not rec_id:
                return invalid_response("No ID Provided", 400)

            try:
                body = json.loads(request.httprequest.data or b"{}")
            except Exception:
                return invalid_response("Invalid JSON Data", 400)

            fields = body.get("fields") or []
            expand = body.get("expand") or {}
            values = body.get("values") or {}

            if not isinstance(fields, list):
                return invalid_response("fields must be a list in body", 400)
            if expand and not isinstance(expand, dict):
                return invalid_response("expand must be a dict in body", 400)
            if not isinstance(values, dict):
                return invalid_response("values must be a dict in body", 400)

            read_fields = list(dict.fromkeys(fields + list(expand.keys())))
            if not read_fields:
                read_fields = ["id"]

            try:
                if method == "POST":
                    new_rec = request.env[model_name].sudo().create(values)
                    records = request.env[model_name].sudo().search_read(
                        domain=[("id", "=", new_rec.id)],
                        fields=read_fields,
                    )
                    for r in records:
                        self._iso_convert(r)
                    records = self._expand_relations(model_name, records, expand)
                    return valid_response(records[0] if records else {}, status=201)

                # PUT
                rec = request.env[model_name].sudo().browse(rec_id)
                if not rec.exists():
                    return invalid_response("Resource not found", 404)

                rec.write(values)
                records = request.env[model_name].sudo().search_read(
                    domain=[("id", "=", rec.id)],
                    fields=read_fields,
                )
                for r in records:
                    self._iso_convert(r)
                records = self._expand_relations(model_name, records, expand)
                return valid_response(records[0] if records else {}, status=200)

            except Exception as e:
                _logger.exception("%s error %s: %s", method, model_name, str(e))
                return invalid_response(str(e), 500)

        # ---------------- DELETE ----------------
        if method == "DELETE":
            if not option.is_delete:
                return invalid_response("Method Not Allowed", 405)
            if not rec_id:
                return invalid_response("No ID Provided", 400)

            try:
                rec = request.env[model_name].sudo().browse(rec_id)
                if not rec.exists():
                    return invalid_response("Resource not found", 404)
                rec.unlink()
                return valid_response({"deleted_id": rec_id}, status=200)
            except Exception as e:
                _logger.exception("DELETE error %s: %s", model_name, str(e))
                return invalid_response(str(e), 500)

        return invalid_response("Unsupported method", 405)