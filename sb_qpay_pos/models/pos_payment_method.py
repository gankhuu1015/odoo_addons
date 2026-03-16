import json
import logging
import uuid

import requests
from requests.auth import HTTPBasicAuth

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    qpay_url = fields.Char(copy=False, groups="point_of_sale.group_pos_manager")
    qpay_username = fields.Char(copy=False, groups="point_of_sale.group_pos_manager")
    qpay_pwd = fields.Char(copy=False, groups="point_of_sale.group_pos_manager")
    qpay_invoice_code = fields.Char(copy=False, groups="point_of_sale.group_pos_manager")

    def _get_payment_terminal_selection(self):
        return super()._get_payment_terminal_selection() + [("qpay", "QPay")]

    def _get_payment_method_type(self):
        return super()._get_payment_method_type() + [("qpay", self.env._("QPay"))]

    @api.depends("type", "payment_method_type", "use_payment_terminal")
    def _compute_hide_use_payment_terminal(self):
        super()._compute_hide_use_payment_terminal()
        for payment_method in self:
            if payment_method.payment_method_type == "qpay":
                payment_method.hide_use_payment_terminal = False

    @api.onchange("payment_method_type")
    def _onchange_payment_method_type(self):
        super()._onchange_payment_method_type()
        for record in self:
            if record.payment_method_type == "qpay":
                record.use_payment_terminal = "qpay"
                record.split_transactions = False

    @staticmethod
    def _force_payment_method_type_values(vals, payment_method_type, if_present=False):
        if payment_method_type == "qpay":
            disabled_fields_name = ["qr_code_method"]
            if if_present:
                for name in disabled_fields_name:
                    if name in vals:
                        vals[name] = False
            else:
                vals["qr_code_method"] = False
            vals["use_payment_terminal"] = "qpay"
            vals["split_transactions"] = False
            return
        if payment_method_type == "terminal":
            disabled_fields_name = ["qr_code_method"]
        elif payment_method_type == "qr_code":
            disabled_fields_name = ["use_payment_terminal"]
        else:
            disabled_fields_name = ["use_payment_terminal", "qr_code_method"]
        if if_present:
            for name in disabled_fields_name:
                if name in vals:
                    vals[name] = False
        else:
            for name in disabled_fields_name:
                vals[name] = False

    @api.constrains("payment_method_type", "use_payment_terminal", "split_transactions", "config_ids", "company_id")
    def _check_qpay_fields(self):
        for rec in self:
            if rec.payment_method_type != "qpay" and rec.use_payment_terminal != "qpay":
                continue
            if rec.use_payment_terminal != "qpay":
                raise ValidationError(_("QPay payment method must use 'qpay' terminal integration."))
            if rec.split_transactions:
                raise ValidationError(_("QPay payment method does not support Identify Customer. Disable it."))
            if any(config.company_id != rec.company_id for config in rec.config_ids):
                raise ValidationError(_("QPay payment method and linked POS configs must belong to the same company."))

    @api.model
    def _load_pos_data_fields(self, config):
        fields_list = super()._load_pos_data_fields(config)
        # Credentials are server-side only; frontend only needs terminal flag and id.
        return fields_list

    @api.model
    def _sb_qpay_pos_next_external_ref(self, company=None):
        company = company or self.env.company
        seq = self.env["ir.sequence"].with_company(company).sudo().next_by_code("sb_qpay_pos.external_ref")
        if seq:
            return seq
        return f"SBQPAY-C{company.id}-{uuid.uuid4().hex[:16].upper()}"

    @staticmethod
    def _sb_qpay_pos_error_text(data, fallback=""):
        if isinstance(data, dict):
            msg = data.get("message") or data.get("msg") or data.get("error_description")
            err = data.get("error")
            if msg and err and msg != err:
                return f"{err}: {msg}"
            return msg or err or fallback
        if isinstance(data, str):
            return data
        return fallback

    def _sb_qpay_pos_get_token(self):
        self.ensure_one()
        if self.use_payment_terminal != "qpay":
            raise ValidationError(_("Selected payment method is not configured for QPay."))
        if not self.qpay_url or not self.qpay_username or not self.qpay_pwd or not self.qpay_invoice_code:
            raise ValidationError(_("Please fill QPay settings on the payment method first."))
        auth_url = f"{self.qpay_url.rstrip('/')}/auth/token"
        try:
            response = requests.post(
                auth_url,
                auth=HTTPBasicAuth(self.qpay_username, self.qpay_pwd),
                timeout=15,
            )
            data = response.json() if response.content else {}
        except requests.RequestException as exc:
            raise ValidationError(_("QPay auth request failed: %s", str(exc))) from exc

        if response.status_code != 200:
            details = self._sb_qpay_pos_error_text(data, response.text or str(response.status_code))
            raise ValidationError(_("QPay auth failed: %s", details))

        token = data.get("access_token")
        if not token:
            raise ValidationError(_("QPay auth failed: access_token missing."))
        return token

    def _sb_qpay_pos_create_invoice(self, amount, external_ref, callback_url, description):
        self.ensure_one()
        token = self._sb_qpay_pos_get_token()
        payload = {
            "invoice_code": self.qpay_invoice_code,
            "sender_invoice_no": external_ref,
            "invoice_receiver_code": "terminal",
            "invoice_description": description,
            "sender_branch_code": "POS",
            "amount": amount,
            "callback_url": callback_url,
            "lines": [{"line_description": description, "line_quantity": "1", "line_unit_price": str(amount), "note": "POS"}],
        }
        try:
            response = requests.post(
                f"{self.qpay_url.rstrip('/')}/invoice",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                data=json.dumps(payload),
                timeout=20,
            )
            data = response.json() if response.content else {}
        except requests.RequestException as exc:
            raise ValidationError(_("QPay invoice request failed: %s", str(exc))) from exc

        if response.status_code != 200:
            details = self._sb_qpay_pos_error_text(data, response.text or str(response.status_code))
            raise ValidationError(_("QPay invoice creation failed: %s", details))

        return data

    def _sb_qpay_pos_check_invoice(self, provider_invoice_id):
        self.ensure_one()
        token = self._sb_qpay_pos_get_token()
        payload = {
            "object_type": "INVOICE",
            "object_id": str(provider_invoice_id),
        }
        try:
            response = requests.post(
                f"{self.qpay_url.rstrip('/')}/payment/check",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                data=json.dumps(payload),
                timeout=20,
            )
            data = response.json() if response.content else {}
        except requests.RequestException as exc:
            raise ValidationError(_("QPay status check failed: %s", str(exc))) from exc

        if response.status_code != 200:
            details = self._sb_qpay_pos_error_text(data, response.text or str(response.status_code))
            raise ValidationError(_("QPay status check failed: %s", details))

        count = int(data.get("count") or 0)
        is_paid = count > 0
        return {
            "is_paid": is_paid,
            "message": _("Payment successful") if is_paid else _("Payment is pending"),
            "provider_response": data,
        }

    def _sb_qpay_pos_cancel_invoice(self, provider_invoice_id):
        self.ensure_one()
        token = self._sb_qpay_pos_get_token()
        try:
            response = requests.delete(
                f"{self.qpay_url.rstrip('/')}/invoice/{provider_invoice_id}",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                timeout=20,
            )
            data = response.json() if response.content else {}
        except requests.RequestException as exc:
            raise ValidationError(_("QPay cancel request failed: %s", str(exc))) from exc

        if response.status_code not in (200, 204):
            details = self._sb_qpay_pos_error_text(data, response.text or str(response.status_code))
            raise ValidationError(_("QPay cancel failed: %s", details))
        return data or {"message": "canceled"}

    @api.model
    def qpay_create_invoice_for_pos(self, payment_method_id, payload):
        payment_method = self.browse(payment_method_id).exists()
        if not payment_method:
            return {"ok": False, "message": _("Payment method not found.")}
        if payment_method.use_payment_terminal != "qpay":
            return {"ok": False, "message": _("Payment method is not QPay.")}

        amount = float(payload.get("amount") or 0)
        if amount <= 0:
            return {"ok": False, "message": _("QPay amount must be greater than zero.")}

        line_uuid = (payload.get("line_uuid") or "").strip()
        if not line_uuid:
            return {"ok": False, "message": _("Missing payment line uuid.")}

        pos_session = self.env["pos.session"].browse(payload.get("session_id")).exists()
        pos_config = pos_session.config_id if pos_session else self.env["pos.config"]
        if pos_session and pos_session.company_id != payment_method.company_id:
            return {"ok": False, "message": _("QPay payment method company does not match POS session company.")}

        idempotency_key = f"{line_uuid}:{amount:.6f}"
        tx = self.env["sb.qpay.pos.transaction"].search(
            [("idempotency_key", "=", idempotency_key), ("payment_method_id", "=", payment_method.id)],
            limit=1,
        )
        if tx and tx.state in {"pending", "paid"}:
            return {
                "ok": True,
                "transaction_id": tx.id,
                "external_ref": tx.external_ref,
                "invoice_id": tx.provider_invoice_id,
                "qr_value": tx.qr_value,
                "state": tx.state,
                "message": tx.last_message or "",
            }

        external_ref = self._sb_qpay_pos_next_external_ref(company=payment_method.company_id)
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        callback_url = f"{base_url.rstrip('/')}/sb_qpay_pos/callback?ref={external_ref}"
        description = (payload.get("description") or "").strip()
        if description == "/":
            description = ""
        if not description:
            order_name = (payload.get("order_name") or "").strip()
            description = "" if order_name == "/" else order_name
        description = description or "POS Payment"
        tx = self.env["sb.qpay.pos.transaction"].create(
            {
                "external_ref": external_ref,
                "idempotency_key": idempotency_key,
                "payment_method_id": payment_method.id,
                "pos_session_id": pos_session.id if pos_session else False,
                "pos_config_id": pos_config.id if pos_config else False,
                "order_uuid": payload.get("order_uuid") or "",
                "line_uuid": line_uuid,
                "currency_id": payload.get("currency_id") or payment_method.company_id.currency_id.id,
                "amount": amount,
                "state": "pending",
            }
        )

        try:
            resp = payment_method._sb_qpay_pos_create_invoice(amount, external_ref, callback_url, description)
            provider_invoice_id = (
                resp.get("invoice_id")
                or resp.get("invoiceId")
                or resp.get("id")
                or resp.get("data", {}).get("invoice_id")
            )
            qr_value = (
                resp.get("qr_text")
                or resp.get("qrText")
                or resp.get("qr_code_text")
                or resp.get("qr")
                or resp.get("data", {}).get("qr_text")
            )
            if not provider_invoice_id:
                tx._mark_failed(_("QPay invoice id missing in response."), resp)
                return {"ok": False, "message": _("QPay invoice id missing in response.")}
            tx.write(
                {
                    "provider_invoice_id": str(provider_invoice_id),
                    "qr_value": qr_value or str(provider_invoice_id),
                    "provider_response": resp,
                    "last_message": _("QPay invoice created."),
                    "state": "pending",
                }
            )
            return {
                "ok": True,
                "transaction_id": tx.id,
                "external_ref": tx.external_ref,
                "invoice_id": tx.provider_invoice_id,
                "qr_value": tx.qr_value,
                "state": tx.state,
                "message": tx.last_message,
            }
        except ValidationError as exc:
            tx._mark_failed(str(exc))
            return {"ok": False, "message": str(exc), "transaction_id": tx.id}

    @api.model
    def qpay_check_invoice_status_for_pos(self, payment_method_id, transaction_id):
        payment_method = self.browse(payment_method_id).exists()
        tx = self.env["sb.qpay.pos.transaction"].browse(transaction_id).exists()
        if not payment_method or not tx or tx.payment_method_id != payment_method:
            return {"ok": False, "message": _("Transaction not found.")}
        if tx.company_id != payment_method.company_id:
            return {"ok": False, "message": _("Company mismatch between transaction and payment method.")}
        if tx.state in {"paid", "failed", "canceled", "expired"}:
            return {
                "ok": True,
                "state": tx.state,
                "message": tx.last_message or "",
                "transaction_id": tx.id,
                "line_uuid": tx.line_uuid,
            }
        if not tx.provider_invoice_id:
            tx._mark_failed(_("Missing provider invoice id."))
            tx._notify_pos()
            return {"ok": False, "state": tx.state, "message": tx.last_message, "transaction_id": tx.id, "line_uuid": tx.line_uuid}

        try:
            status = payment_method._sb_qpay_pos_check_invoice(tx.provider_invoice_id)
        except ValidationError as exc:
            tx._mark_pending(str(exc))
            return {
                "ok": False,
                "state": tx.state,
                "message": tx.last_message,
                "transaction_id": tx.id,
                "line_uuid": tx.line_uuid,
            }

        if status["is_paid"]:
            tx._mark_paid(status["message"], status["provider_response"])
        else:
            tx._mark_pending(status["message"], status["provider_response"])
        tx._notify_pos()
        return {
            "ok": True,
            "state": tx.state,
            "message": tx.last_message or "",
            "transaction_id": tx.id,
            "line_uuid": tx.line_uuid,
        }

    @api.model
    def qpay_handle_callback_for_pos(self, external_ref, payload=None):
        tx = self.env["sb.qpay.pos.transaction"].search([("external_ref", "=", external_ref)], limit=1)
        if not tx:
            _logger.warning("QPay callback ignored: unknown external_ref=%s", external_ref)
            return {"ok": False, "message": "unknown external_ref"}

        tx.write({"callback_payload": payload or {}})
        result = self.qpay_check_invoice_status_for_pos(tx.payment_method_id.id, tx.id)
        return result

    @api.model
    def qpay_cancel_invoice_for_pos(self, payment_method_id, transaction_id):
        payment_method = self.browse(payment_method_id).exists()
        tx = self.env["sb.qpay.pos.transaction"].browse(transaction_id).exists()
        if not payment_method or not tx or tx.payment_method_id != payment_method:
            return {"ok": False, "message": _("Transaction not found.")}
        if tx.company_id != payment_method.company_id:
            return {"ok": False, "message": _("Company mismatch between transaction and payment method.")}

        if tx.state == "paid":
            return {
                "ok": True,
                "state": "paid",
                "message": tx.last_message or _("Payment already completed."),
                "transaction_id": tx.id,
                "line_uuid": tx.line_uuid,
            }
        if tx.state in {"canceled", "failed", "expired"}:
            return {
                "ok": True,
                "state": tx.state,
                "message": tx.last_message or "",
                "transaction_id": tx.id,
                "line_uuid": tx.line_uuid,
            }

        if not tx.provider_invoice_id:
            tx._mark_canceled(_("Invoice canceled from POS."))
            tx._notify_pos()
            return {
                "ok": True,
                "state": tx.state,
                "message": tx.last_message or "",
                "transaction_id": tx.id,
                "line_uuid": tx.line_uuid,
            }

        try:
            cancel_response = payment_method._sb_qpay_pos_cancel_invoice(tx.provider_invoice_id)
            tx._mark_canceled(_("Invoice canceled from POS."), cancel_response)
        except ValidationError as exc:
            tx._mark_pending(str(exc))
            return {
                "ok": False,
                "state": tx.state,
                "message": tx.last_message or "",
                "transaction_id": tx.id,
                "line_uuid": tx.line_uuid,
            }
        tx._notify_pos()
        return {
            "ok": True,
            "state": tx.state,
            "message": tx.last_message or "",
            "transaction_id": tx.id,
            "line_uuid": tx.line_uuid,
        }

    @api.model
    def _sb_qpay_pos_ensure_default_method(self, company=None):
        company = company or self.env.company
        existing = self.with_company(company).search(
            [("use_payment_terminal", "=", "qpay"), ("company_id", "=", company.id)],
            limit=1,
        )
        if existing:
            if not existing.open_session_ids:
                existing.write(
                    {
                        "payment_method_type": "qpay",
                        "split_transactions": False,
                        "use_payment_terminal": "qpay",
                    }
                )
            return existing

        journal = self.env["account.journal"].with_company(company).search(
            [("type", "=", "bank"), ("company_id", "=", company.id)],
            limit=1,
        )
        if not journal:
            return False

        vals = {
            "name": "QPay",
            "journal_id": journal.id,
            "payment_method_type": "qpay",
            "use_payment_terminal": "qpay",
            "split_transactions": False,
            "company_id": company.id,
        }
        return self.with_company(company).create(vals)
