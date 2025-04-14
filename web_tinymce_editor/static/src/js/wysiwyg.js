odoo.define("aspl_web_tinymce_editor.wysiwyg", function (require) {
    "use strict";
  
    var Wysiwyg = require("web_editor.wysiwyg");
    const TinyMceWysiwyg= Wysiwyg.extend({
        /**
         * @override
         */
        init: function(parent, options) {
            this._super.apply(this, arguments);
            // Ensure default options are set
            this.options = options || {};
            this.options.sanitize_tags = this.options.sanitize_tags || true;
        },
  
        startEdition: async function() {
            try {
                await this._super(...arguments);
                this.$editable.on("mousedown", (e) => {
                    if ($(e.target).is(".o_editable:empty") || e.target.querySelector(".o_editable")) {
                        e.preventDefault();
                    }
                });
                return true;
            } catch (error) {
                console.error("Editor initialization failed:", error);
            }
        },
  
        // ... rest of your methods remain the same ...
    });
  
    return TinyMceWysiwyg;
  });