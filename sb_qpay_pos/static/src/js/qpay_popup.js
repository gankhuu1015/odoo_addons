/** @odoo-module **/

import { Component } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

export class QPayPosPopup extends Component {
    static template = "sb_qpay_pos.QPayPosPopup";
    static components = { Dialog };
    static props = {
        qrSrc: String,
        formattedAmount: String,
        externalRef: String,
        onCheck: Function,
        close: Function,
    };

    async onClickCheck() {
        await this.props.onCheck();
    }

    onClickClose() {
        this.props.close();
    }
}
