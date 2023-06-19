/** @odoo-module **/

import { HtmlField } from "@web_editor/js/backend/html_field";
import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
const { onWillStart, onMounted, useEffect, useSubEnv, onWillUpdateProps } = owl;
import { useService } from "@web/core/utils/hooks";
import { getWysiwygClass } from "web_editor.loader";
import { toInline } from "web_editor.convertInline";
import { loadJS } from "@web/core/assets";
export class TinyInit extends HtmlField {
  setup() {
    super.setup();
    useSubEnv({
      onWysiwygReset: this._resetIframe.bind(this),
    });
    this.action = useService("action");
    this.rpc = useService("rpc");
    this.dialog = useService("dialog");
    onWillStart(async () => {
      await loadJS("web_tinymce_editor/static/lib/tinymce/tinymce.min.js");
    });
    useEffect(
      () => {
        const listener = () => {
          this._lastClickInIframe = false;
        };
        document.addEventListener("mousedown", listener, true);

        return () => document.removeEventListener("mousedown", listener, true);
      },
      () => []
    );
  }
  get wysiwygOptions() {
    return {
      ...super.wysiwygOptions,
      onIframeUpdated: () => this.onIframeUpdated(),
      resizable: false,
      defaultDataForLinkTools: { isNewWindow: true },
      ...this.props.wysiwygOptions,
    };
  }

  async commitChanges() {
    if (this.props.readonly || !this.isRendered) {
      return super.commitChanges();
    }
    const $editable = this.wysiwyg.getEditable();
    await this.wysiwyg.cleanForSave();
    await this.wysiwyg.saveModifiedImages(this.$content);
    await super.commitChanges();
    const $editorEnable = $editable.closest(".editor_enable");
    $editorEnable.removeClass("editor_enable");
    this.wysiwyg.odooEditor.observerUnactive("toInline");
    var myContent = tinymce.activeEditor.getContent();
    this.wysiwyg.$editable.html($(myContent).html());
    $editorEnable.addClass("editor_enable");
    await super.commitChanges();
  }

  async startWysiwyg(...args) {
    await super.startWysiwyg(...args);
    setTimeout(async () => {
      tinymce.remove;
      tinymce.init({
        selector: ".tiny_test_init",
        plugins:
          "anchor autolink charmap codesample emoticons image link lists media searchreplace table visualblocks wordcount checklist mediaembed casechange export formatpainter pageembed linkchecker a11ychecker tinymcespellchecker permanentpen powerpaste advtable advcode editimage tinycomments tableofcontents footnotes mergetags autocorrect typography inlinecss",
        toolbar:
          "undo redo | blocks fontfamily fontsize | bold italic underline strikethrough | link image media table mergetags | addcomment showcomments | spellcheckdialog a11ycheck typography | align lineheight | checklist numlist bullist indent outdent | emoticons charmap | removeformat",
        tinycomments_mode: "embedded",
        tinycomments_author: "Author name",
        mergetags_list: [
          { value: "First.Name", title: "First Name" },
          { value: "Email", title: "Email" },
        ],
      });
    }, 1000);
    await this._resetIframe();
  }

  async _resetIframe() {
    this.wysiwyg.$editable.find(".o_layout").addBack().data("name", "pdf");
    this.wysiwyg.odooEditor.observerFlush();
    this.wysiwyg.odooEditor.historyReset();

    this.wysiwyg.odooEditor.document.addEventListener(
      "mousedown",
      () => {
        let count = 0;
        count += 1;
        this._lastClickInIframe = true;
        const fieldName = this.props.inlineField;
        return this.props.record.update({
          [fieldName]: this._unWrap(count),
        });
      },
      true
    );
  }
  async _getWysiwygClass() {
    return getWysiwygClass({ moduleName: "web_tinymce_editor.wysiwyg" });
  }

  _onWysiwygBlur() {
    if (!this._lastClickInIframe) {
      super._onWysiwygBlur();
    }
  }
}

TinyInit.props = {
  ...standardFieldProps,
  ...HtmlField.props,
  inlineField: { type: String, optional: true },
};

TinyInit.displayName = _lt("Email");
TinyInit.extractProps = (...args) => {
  const [{ attrs }] = args;
  const htmlProps = HtmlField.extractProps(...args);
  return {
    ...htmlProps,
    inlineField: attrs.options["inline-field"],
  };
};
registry.category("fields").add("tiny_init", TinyInit);
