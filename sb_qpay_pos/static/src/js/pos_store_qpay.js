/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);

        // Recover from browser refresh: avoid leaving QPay lines stuck in waiting state
        // without an active popup flow.
        for (const order of this.models["pos.order"].getAll()) {
            for (const line of order.payment_ids || []) {
                if (
                    line.payment_method_id?.use_payment_terminal === "qpay" &&
                    ["waiting", "waitingCard", "timeout", "waitingCancel"].includes(
                        line.getPaymentStatus?.() || ""
                    )
                ) {
                    line.setPaymentStatus("retry");
                }
            }
        }

        this.data.connectWebSocket("SB_QPAY_POS_PAYMENT_UPDATE", (payload) => {
            const pendingLine = this.getPendingPaymentLine("qpay");
            if (pendingLine) {
                pendingLine.payment_method_id.payment_terminal?.handleQPayStatusUpdate(payload);
            }
        });
    },
});
