import uuid

from odoo import fields, models


class QPayPosTransaction(models.Model):
    _name = "sb.qpay.pos.transaction"
    _description = "SB QPay POS Transaction"
    _order = "id desc"

    name = fields.Char(required=True, default=lambda self: self.env._("New"), copy=False)
    external_ref = fields.Char(required=True, index=True, copy=False)
    idempotency_key = fields.Char(required=True, index=True, copy=False)

    payment_method_id = fields.Many2one("pos.payment.method", required=True, ondelete="restrict", index=True)
    company_id = fields.Many2one("res.company", related="payment_method_id.company_id", store=True, index=True)
    pos_session_id = fields.Many2one("pos.session", index=True, ondelete="set null")
    pos_config_id = fields.Many2one("pos.config", index=True, ondelete="set null")

    order_uuid = fields.Char(index=True)
    line_uuid = fields.Char(required=True, index=True)

    currency_id = fields.Many2one("res.currency", required=True, ondelete="restrict")
    amount = fields.Monetary(required=True, currency_field="currency_id")

    provider_invoice_id = fields.Char(index=True)
    qr_value = fields.Text()

    state = fields.Selection(
        [
            ("pending", "Pending"),
            ("paid", "Paid"),
            ("failed", "Failed"),
            ("canceled", "Canceled"),
            ("expired", "Expired"),
        ],
        default="pending",
        required=True,
        index=True,
        copy=False,
    )
    paid_at = fields.Datetime(copy=False)
    last_message = fields.Text(copy=False)
    callback_payload = fields.Json(copy=False)
    provider_response = fields.Json(copy=False)

    _sql_constraints = [
        ("sb_qpay_pos_transaction_external_ref_uniq", "unique(external_ref)", "QPay external reference must be unique."),
        ("sb_qpay_pos_transaction_idempotency_uniq", "unique(idempotency_key)", "QPay idempotency key must be unique."),
    ]

    def _notify_pos(self):
        for tx in self:
            if tx.pos_config_id:
                tx.pos_config_id._notify(
                    "SB_QPAY_POS_PAYMENT_UPDATE",
                    {
                        "transaction_id": tx.id,
                        "line_uuid": tx.line_uuid,
                        "state": tx.state,
                        "message": tx.last_message or "",
                    },
                )

    def _mark_pending(self, message=None, provider_response=None):
        vals = {"state": "pending"}
        if message is not None:
            vals["last_message"] = message
        if provider_response is not None:
            vals["provider_response"] = provider_response
        self.write(vals)

    def _mark_paid(self, message=None, provider_response=None):
        vals = {"state": "paid", "paid_at": fields.Datetime.now()}
        if message is not None:
            vals["last_message"] = message
        if provider_response is not None:
            vals["provider_response"] = provider_response
        self.write(vals)

    def _mark_failed(self, message=None, provider_response=None):
        vals = {"state": "failed"}
        if message is not None:
            vals["last_message"] = message
        if provider_response is not None:
            vals["provider_response"] = provider_response
        self.write(vals)

    def _mark_canceled(self, message=None, provider_response=None):
        vals = {"state": "canceled"}
        if message is not None:
            vals["last_message"] = message
        if provider_response is not None:
            vals["provider_response"] = provider_response
        self.write(vals)

    @classmethod
    def _new_external_ref(cls):
        return uuid.uuid4().hex
