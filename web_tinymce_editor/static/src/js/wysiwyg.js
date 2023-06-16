odoo.define("web_tinymce_editor.wysiwyg", function (require) {
  "use strict";

  var Wysiwyg = require("web_editor.wysiwyg");
  const {
    closestElement,
  } = require("@web_editor/js/editor/odoo-editor/src/OdooEditor");

  const tinymce_editorWysiwyg = Wysiwyg.extend({
    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    startEdition: async function () {
      const res = await this._super(...arguments);
      // Prevent selection change outside of snippets.
      this.$editable.on("mousedown", (e) => {
        if (
          $(e.target).is(".o_editable:empty") ||
          e.target.querySelector(".o_editable")
        ) {
          e.preventDefault();
        }
      });
      return res;
    },

    toggleLinkTools(options) {
      this._super({
        ...options,
        // Always open the dialog for the basic theme as it has no sidebar.
        forceDialog:
          options.forceDialog || this.$iframeBody.find(".o_basic_theme").length,
      });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _getPowerboxOptions: function () {
      const options = this._super();
      const { commands } = options;
      const linkCommands = commands.filter(
        (command) => command.name === "Link" || command.name === "Button"
      );
      for (const linkCommand of linkCommands) {
        // Remove the command if the selection is within a background-image.
        const superIsDisabled = linkCommand.isDisabled;
        linkCommand.isDisabled = () => {
          if (superIsDisabled && superIsDisabled()) {
            return true;
          } else {
            const selection = this.odooEditor.document.getSelection();
            const range = selection.rangeCount && selection.getRangeAt(0);
            return (
              !!range &&
              !!closestElement(
                range.startContainer,
                "[style*=background-image]"
              )
            );
          }
        };
      }
      return { ...options, commands };
    },
    /**
     * @override
     */
    _updateEditorUI: function (e) {
      this._super(...arguments);
      // Hide the create-link button if the selection is within a
      // background-image.
      const selection = this.odooEditor.document.getSelection();
      const range = selection.rangeCount && selection.getRangeAt(0);
      const isWithinBackgroundImage =
        !!range &&
        !!closestElement(range.startContainer, "[style*=background-image]");
      if (isWithinBackgroundImage) {
        this.toolbar.$el.find("#create-link").toggleClass("d-none", true);
      }
    },
  });

  return tinymce_editorWysiwyg;
});
