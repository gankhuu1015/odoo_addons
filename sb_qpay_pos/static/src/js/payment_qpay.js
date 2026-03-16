/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { PaymentInterface } from "@point_of_sale/app/utils/payment/payment_interface";
import { register_payment_method } from "@point_of_sale/app/services/pos_store";
import { QPayPosPopup } from "@sb_qpay_pos/js/qpay_popup";

export class PaymentQPay extends PaymentInterface {
    setup() {
        super.setup(...arguments);
        this.orm = this.env.services.orm;
        this.dialog = this.env.services.dialog;
        this.paymentLineResolvers = {};
        this.pendingFlows = {};
    }

    async sendPaymentRequest(uuid) {
        await super.sendPaymentRequest(...arguments);
        const order = this.pos.getOrder();
        const line = order.payment_ids.find((pl) => pl.uuid === uuid) || order.getSelectedPaymentline();
        if (!line) {
            this._showError(_t("No payment line selected."));
            return false;
        }
        if (line.amount <= 0) {
            this._showError(_t("QPay amount must be greater than zero."));
            return false;
        }

        const payload = {
            amount: line.amount,
            line_uuid: line.uuid,
            session_id: order.session_id?.id,
            order_uuid: order.uuid,
            order_name: order.name,
            currency_id: this.pos.currency?.id,
            description: (order.name || "").trim(),
        };

        let response;
        try {
            response = await this.orm.call("pos.payment.method", "qpay_create_invoice_for_pos", [
                this.payment_method_id.id,
                payload,
            ]);
        } catch {
            this._showError(_t("QPay invoice үүсгэх үед алдаа гарлаа."));
            return false;
        }

        if (!response?.ok) {
            this._showError(response?.message || _t("QPay invoice үүсгэж чадсангүй."));
            return false;
        }

        line.setPaymentStatus("waitingCard");
        line.payment_ref_no = response.external_ref || "";
        line.transaction_id = response.invoice_id || "";

        return this.waitForPaymentConfirmation(uuid, response);
    }

    async sendPaymentCancel(order, uuid) {
        await super.sendPaymentCancel(...arguments);
        const line = order?.payment_ids?.find((pl) => pl.uuid === uuid);
        const txId = this.pendingFlows?.[uuid]?.transactionId;
        if (!line || !txId) {
            return true;
        }
        try {
            const result = await this.orm.call("pos.payment.method", "qpay_cancel_invoice_for_pos", [
                this.payment_method_id.id,
                txId,
            ]);
            if (result?.state === "paid") {
                this._resolveFlow(uuid, true);
                return false;
            }
        } catch {
            return false;
        }
        this._resolveFlow(uuid, false);
        return true;
    }

    waitForPaymentConfirmation(uuid, invoiceData) {
        const order = this.pos.getOrder();
        const line = order.payment_ids.find((pl) => pl.uuid === uuid) || order.getSelectedPaymentline();
        const qrValue = invoiceData.qr_value || invoiceData.invoice_id || invoiceData.external_ref;
        const qrSrc = `/report/barcode/?barcode_type=QR&value=${encodeURIComponent(qrValue)}&width=220&height=220&quiet=0`;

        return new Promise((resolve) => {
            this.paymentLineResolvers[uuid] = resolve;
            const closePopup = this.dialog.add(
                QPayPosPopup,
                {
                    qrSrc,
                    formattedAmount: this.env.utils.formatCurrency(line.amount),
                    externalRef: invoiceData.external_ref || "",
                    onCheck: () => this.manualCheck(uuid),
                },
                {
                    onClose: () => {
                        const flow = this.pendingFlows[uuid];
                        if (!flow || flow.isResolved) {
                            return;
                        }
                        this._handleUserClose(uuid);
                    },
                }
            );

            const intervalId = setInterval(() => {
                this._checkTransaction(uuid, false);
            }, 3000);

            this.pendingFlows[uuid] = {
                uuid,
                lineUuid: uuid,
                transactionId: invoiceData.transaction_id,
                closePopup,
                intervalId,
                isResolved: false,
            };
        });
    }

    async manualCheck(uuid) {
        await this._checkTransaction(uuid, true);
    }

    async _handleUserClose(uuid) {
        const flow = this.pendingFlows[uuid];
        if (!flow || flow.isResolved) {
            return;
        }

        let result;
        try {
            result = await this.orm.call("pos.payment.method", "qpay_cancel_invoice_for_pos", [
                this.payment_method_id.id,
                flow.transactionId,
            ]);
        } catch {
            this._resolveFlow(uuid, false);
            return;
        }

        if (result?.state === "paid") {
            this._resolveFlow(uuid, true);
            return;
        }
        this._resolveFlow(uuid, false);
    }

    async _checkTransaction(uuid, showPendingMessage) {
        const flow = this.pendingFlows[uuid];
        if (!flow || flow.isResolved) {
            return;
        }
        let result;
        try {
            result = await this.orm.call("pos.payment.method", "qpay_check_invoice_status_for_pos", [
                this.payment_method_id.id,
                flow.transactionId,
            ]);
        } catch {
            if (showPendingMessage) {
                this._showError(_t("QPay төлөв шалгах үед алдаа гарлаа."));
            }
            return;
        }

        this._handleStatusResult(uuid, result, showPendingMessage);
    }

    _handleStatusResult(uuid, result, showPendingMessage = false) {
        const flow = this.pendingFlows[uuid];
        if (!flow || flow.isResolved) {
            return;
        }

        if (result?.state === "paid") {
            this._resolveFlow(uuid, true);
            return;
        }

        if (["failed", "canceled", "expired"].includes(result?.state)) {
            this._showError(result?.message || _t("QPay payment failed."));
            this._resolveFlow(uuid, false);
            return;
        }

        if (showPendingMessage) {
            this.dialog.add(AlertDialog, {
                title: _t("QPay Status"),
                body: result?.message || _t("Төлбөр хүлээгдэж байна."),
            });
        }
    }

    handleQPayStatusUpdate(payload) {
        const pendingLine = this.pos.getPendingPaymentLine("qpay");
        if (!pendingLine || pendingLine.uuid !== payload?.line_uuid) {
            return;
        }
        this._handleStatusResult(pendingLine.uuid, payload, false);
    }

    _resolveFlow(uuid, success) {
        const flow = this.pendingFlows[uuid];
        if (!flow || flow.isResolved) {
            return;
        }
        flow.isResolved = true;
        if (flow.intervalId) {
            clearInterval(flow.intervalId);
        }
        if (flow.closePopup) {
            flow.closePopup();
        }

        const resolver = this.paymentLineResolvers?.[uuid];
        if (resolver) {
            resolver(success);
            delete this.paymentLineResolvers[uuid];
        }
        delete this.pendingFlows[uuid];
    }

    _showError(message) {
        this.dialog.add(AlertDialog, {
            title: _t("QPay Error"),
            body: message,
        });
    }
}

register_payment_method("qpay", PaymentQPay);
