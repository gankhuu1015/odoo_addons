/** @odoo-module **/

import { HtmlField } from "@web_editor/js/backend/html_field";
import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
const { onWillStart, useEffect, useSubEnv } = owl;
import { useService } from "@web/core/utils/hooks";
import { getWysiwygClass } from "web_editor.loader";
import { loadBundle } from "@web/core/assets";

export class TinyInit extends HtmlField {
  setup() {
    super.setup();
    useSubEnv({
      onWysiwygReset: this._resetIframe.bind(this),
    });

    // Initialize Odoo services like action, rpc, and dialog
    this.action = useService("action");
    this.rpc = useService("rpc");
    this.dialog = useService("dialog");

  }

  // Getter for WYSIWYG options, overriding some default options
  get wysiwygOptions() {
    return {
      ...super.wysiwygOptions,
      onIframeUpdated: () => this.onIframeUpdated(),
      resizable: false, // Disable resizing of the editor
      defaultDataForLinkTools: { isNewWindow: true }, // Default for links opening in a new window
      onWysiwygBlur: () => {
        this.commitChanges();
        this.wysiwyg.odooEditor.toolbarHide();
    },
      ...this.props.wysiwygOptions, // Allow custom WYSIWYG options passed from props
    };
  }

  async commitChanges() {
    if (this.props.readonly || !this.isRendered) {
      return await super.commitChanges();
    }

    // Get the editable content from the TinyMCE editor
    const $editable = this.wysiwyg.getEditable();
    await this.wysiwyg.cleanForSave();
    await this.wysiwyg.saveModifiedImages(this.$content);

    // Disable editor temporarily during save
    const $editorEnable = $editable.closest(".editor_enable");
    $editorEnable.removeClass("editor_enable"); 
    const fieldName = this.props.inlineField;
    this.wysiwyg.odooEditor.observerUnactive("toInline");
    var myContent = tinymce.activeEditor.getContent();
    this.wysiwyg.$editable.html(myContent);
    $editorEnable.addClass("editor_enable");
    await super.commitChanges();
  }


  _onContentChanged() {
      const content = tinymce.activeEditor.getContent();
      this._lastClickInIframe = true;
      const fieldName = this.props.fieldName;
      return this.props.record.update({
        [fieldName]: this._unWrap(content),
      });
    }

      async startWysiwyg(...args) {
            await super.startWysiwyg(...args);
            await loadBundle({
              jsLibs: [
                  '/aspl_web_tinymce_editor/static/lib/tinymce/tinymce.min.js'
              ],
          });
          if (typeof tinymce !== 'undefined') {
              setTimeout(async () => {
                tinymce.remove;
                tinymce.init({
                  selector: ".o_field_tiny_init",
                  height: 300,
                  plugins:
                    "anchor autolink charmap codesample emoticons image link lists media searchreplace table visualblocks wordcount", // TinyMCE plugins
                  toolbar:
                    "undo redo | blocks fontfamily fontsize | bold italic underline strikethrough | link image media table | align lineheight | numlist bullist indent outdent | emoticons charmap | removeformat", 
                    setup: (editor) => {
                      editor.on('change', () => {
                          this._onContentChanged();
                      });
                  }
                  });
              }, 5);
            }
            await this._resetIframe();
      }

  // Reset the TinyMCE iframe state, removing unnecessary UI elements
  async _resetIframe() {
    const tableContainer = this.wysiwyg.odooEditor._tableUiContainer;
    const collabSelectionsContainer = this.wysiwyg.odooEditor._collabSelectionsContainer;

    if (tableContainer) {
      tableContainer.remove();
    }
    if (collabSelectionsContainer) {
      collabSelectionsContainer.remove();
    }
    this.wysiwyg.$editable.find(".o_layout").addBack().data("name", "pdf");
    this.wysiwyg.odooEditor.observerFlush();
    this.wysiwyg.odooEditor.historyReset();
    this.onIframeUpdated();
  }

  async _getWysiwygClass() {
    return getWysiwygClass({ moduleName: "aspl_web_tinymce_editor.wysiwyg" });
  }

  // Blur event handler for WYSIWYG editor
  _onWysiwygBlur() {
    if (!this._lastClickInIframe) {
      super._onWysiwygBlur();
    }
  }
}

TinyInit.props = {
  ...standardFieldProps,
  ...HtmlField.props,
  inlineField: { type: String, optional: true }
};

TinyInit.displayName = _lt("TinyMce");

TinyInit.extractProps = (...args) => {
  const [{ attrs }] = args;
  const htmlProps = HtmlField.extractProps(...args);
  return {
    ...htmlProps,
    inlineField: attrs.options["inline-field"]
  };
};

// Register the TinyInit field in Odoo's fields registry
registry.category("fields").add("tiny_init", TinyInit);
