// Hospital shared long-form dictation insertion. Pure and QML JS compatible.
// Never submit/save; only append validated local transcription to an editor.
function appendTranscription(currentText, spokenText, maximumLength) {
    const prior = String(currentText === null || currentText === undefined
        ? "" : currentText);
    const spoken = String(spokenText === null || spokenText === undefined
        ? "" : spokenText).replace(/\s+/g, " ").trim();
    const cap = Math.min(16000, Math.max(1, Number(maximumLength || 4000)));
    if (!spoken || /[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/.test(spoken))
        return {accepted:false, text:prior, reason:"NO USABLE SPEECH DETECTED"};
    const joiner = prior.length > 0 && !/\s$/.test(prior) ? " " : "";
    const next = prior + joiner + spoken;
    if (next.length > cap)
        return {accepted:false, text:prior,
            reason:"TEXT LIMIT REACHED // ORIGINAL DRAFT PRESERVED"};
    return {accepted:true, text:next, reason:"DICTATION INSERTED // REVIEW BEFORE SAVING",
        submitted:false, saved:false, launched:false};
}
