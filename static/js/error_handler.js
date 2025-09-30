// error_handler.js - Central API error envelope handling
(function () {
  const FORMAT_HINT = "Formatos aceitos: wav, mp3, ogg, flac, m4a, aac, webm";
  const TYPE_HINTS = {
    format_error: FORMAT_HINT,
    alignment_error:
      "Verifique se o texto corresponde ao áudio e reduza ruído de fundo.",
    upload_error: "Confirme campo de upload e tamanho máximo permitido.",
    system_unavailable: "Reinicie componentes ou aguarde recursos liberarem.",
    unexpected_error:
      "Tente novamente. Se persistir, verifique logs do servidor.",
  };
  function deriveMessage(env) {
    if (!env) return "Erro desconhecido";
    const base = env.error || env.message || "Operação falhou";
    const type = env.error_type;
    const hint = TYPE_HINTS[type] ? `\n${TYPE_HINTS[type]}` : "";
    return type ? `${base} (${type})${hint}` : base;
  }
  function handleEnvelope(env, opts) {
    opts = opts || {};
    try {
      if (!window.app && !opts.toasts) {
        return;
      }
      const toasts = opts.toasts || (window.app && window.app.errorToasts);
      if (!toasts) {
        return;
      }
      if (env && env.success === false) {
        const msg = deriveMessage(env);
        toasts.show(msg, { level: "error", autoDismiss: true });
      }
    } catch (e) {
      console.warn("Error handler exception", e);
    }
  }
  window.ApiError = { handle: handleEnvelope, deriveMessage };
})();
