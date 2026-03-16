import json
import logging

from odoo.http import Controller, Response, request, route

_logger = logging.getLogger(__name__)


class SBQPayPosController(Controller):
    @route("/sb_qpay_pos/callback", type="http", auth="public", methods=["POST"], csrf=False)
    def qpay_callback(self, ref=None, **kwargs):
        raw_body = request.httprequest.get_data()
        payload = {}
        if raw_body:
            try:
                payload = json.loads(raw_body.decode("utf-8"))
            except ValueError:
                payload = {"raw": raw_body.decode("utf-8", errors="ignore")}

        if not ref:
            _logger.warning("QPay callback rejected: missing ref")
            return Response("missing ref", status=400)

        request.env["pos.payment.method"].sudo().qpay_handle_callback_for_pos(ref, payload)
        return Response("ok", status=200)
