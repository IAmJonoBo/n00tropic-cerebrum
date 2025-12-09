/**
 * Antora extension wrapper for asciidoctor-kroki
 *
 * This file properly registers the Kroki extension with Antora's
 * extension system to enable diagram rendering.
 */

module.exports.register = function () {
  // Register the asciidoctor-kroki extension
  this.once("contextStarted", ({ playbook }) => {
    // The extension will be auto-registered when required
    require("asciidoctor-kroki");
  });
};
