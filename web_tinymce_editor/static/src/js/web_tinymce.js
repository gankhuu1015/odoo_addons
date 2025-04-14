/** @odoo-module **/

import { HtmlField } from "@web_editor/js/backend/html_field";
import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
const { onMounted, useSubEnv } = owl;
import { useService } from "@web/core/utils/hooks";
import { getWysiwygClass } from "web_editor.loader";
import { loadBundle } from "@web/core/assets";

export class TinyInit extends HtmlField {
  setup() {
    super.setup();
    useSubEnv({
      onWysiwygReset: this._resetIframe.bind(this),
    });

    this.action = useService("action");
    this.rpc = useService("rpc");
    this.dialog = useService("dialog");
    this.orm = useService("orm");

    this.originalContent = this.props.value || "";
    onMounted(() => this.initializeTinyMCE());
    this._patchFormButtons();

  }
  _patchFormButtons() {
    setTimeout(() => {

        const previouBtn = document.querySelector(".o_pager_previous");
        const nexBtn = document.querySelector(".o_pager_next");
        const modelName = this.props.record.resModel;
        const fieldName = this.props.fieldName;
        const resIds = this.props.record.resIds;
        
        const loadAndUpdate = async (targetId) => {
            const [result] = await this.orm.read(modelName, [targetId], [fieldName]);
            if (result) {
                tinymce.activeEditor.setContent(result[fieldName]);
                this.originalContent = result[fieldName]
            }
        };
        
        if (previouBtn) {
            previouBtn.addEventListener("click", async () => {
                const resId = this.props.record.resId;
                const currentIndex = resIds.indexOf(resId);
                const prevId = currentIndex === 0 ? resIds[resIds.length - 1] : resIds[currentIndex - 1];
                loadAndUpdate(prevId);
            });
        }

        if (nexBtn) {
            nexBtn.addEventListener("click", async () => {
                const resId = this.props.record.resId;
                const currentIndex = resIds.indexOf(resId);
                const nextId = currentIndex === resIds.length - 1 ? resIds[0] : resIds[currentIndex + 1];
                loadAndUpdate(nextId);
            });
        }

        const saveBtn = document.querySelector(".o_form_button_save");
        const cancelBtn = document.querySelector(".o_form_button_cancel");
        if (saveBtn) {
            saveBtn.addEventListener("click", () => {
                this.commitChanges();
            });
        }
        if (cancelBtn) {
            cancelBtn.addEventListener("click", () => {
                if (typeof tinymce !== 'undefined' && tinymce.activeEditor) {
                    tinymce.activeEditor.setContent(this.originalContent);
                }
            });
        }
        }, 400);
    }

  get wysiwygOptions() {
    return {
      ...super.wysiwygOptions,
      onIframeUpdated: () => this.onIframeUpdated(),
      resizable: false,
      defaultDataForLinkTools: { isNewWindow: true },
      onWysiwygBlur: () => {
        this.commitChanges();
        this.wysiwyg.odooEditor.toolbarHide();
    },
      ...this.props.wysiwygOptions,
    };
  }

  async commitChanges() {
    const $editable = this.wysiwyg.getEditable();

    await this.wysiwyg.cleanForSave();
    await this.wysiwyg.saveModifiedImages(this.$content);

    const $editorEnable = $editable.closest(".editor_enable");
    $editorEnable.removeClass("editor_enable"); 
    this.wysiwyg.odooEditor.observerUnactive("toInline");
    var myContent = tinymce.activeEditor.getContent();
    this.wysiwyg.$editable.html(myContent);
    this.originalContent = myContent
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

    async initializeTinyMCE() {
        await loadBundle({
            jsLibs: [
                '/web_tinymce_editor/static/lib/tinymce/tinymce.min.js'
            ],
        });

        if (typeof tinymce !== 'undefined') {
                tinymce.init({
                    selector: ".o_field_tiny_init",
                    height: 400,
                    license_key: 'gpl',
                    plugins:
                    "anchor autolink charmap codesample emoticons image link lists media searchreplace table visualblocks wordcount", // TinyMCE plugins
                    toolbar:
                    "undo redo | blocks fontfamily fontsize | bold italic underline strikethrough | link image media table | align lineheight | numlist bullist indent outdent | emoticons charmap | removeformat", 
                    setup: (editor) => {
                        editor.on('change', () => {
                            this._onContentChanged();
                        });
                        editor.on('init', () => {
                        if (this.props.value) {
                            editor.setContent(this.props.value);
                        }
                    });
                    }
                });
        }
    }

    async startWysiwyg(...args) {
        await super.startWysiwyg(...args);
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
    return getWysiwygClass({ moduleName: "web_tinymce_editor.wysiwyg" });
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
