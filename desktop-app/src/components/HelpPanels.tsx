import { CircleHelp, Keyboard, Sparkles, Wand2 } from "lucide-react";

export function KeyboardShortcutsPanel() {
  const shortcuts = [
    ["Ctrl+S", "Save project"],
    ["Ctrl+O", "Open project"],
    ["Ctrl+Enter", "Generate preview render"],
    ["Ctrl+Z", "Undo inside active editor/timeline"],
    ["Ctrl+Y", "Redo inside active editor/timeline"],
    ["Delete", "Ripple delete selected timeline scene"],
    ["Arrow Left / Right", "Nudge selected scene by snap amount"],
    ["Shift+Arrow", "Nudge selected scene faster"]
  ];
  return (
    <div className="shortcut-panel">
      <section className="wide-panel">
        <h2><Keyboard size={16} /> Keyboard Shortcuts</h2>
        <div className="shortcut-grid">
          {shortcuts.map(([keys, label]) => (
            <span key={keys}><kbd>{keys}</kbd><strong>{label}</strong></span>
          ))}
        </div>
      </section>
    </div>
  );
}

export function HelpCenter({ onOpenDocs, onOpenShortcuts }: { onOpenDocs: () => void; onOpenShortcuts: () => void }) {
  const prompts = [
    "Make this into a YouTube Short with clean captions.",
    "Create a premium cinematic product showcase from this screen recording.",
    "Find the strongest moments, remove dead air, and add smooth zooms.",
    "Make this tutorial clear, slower paced, and easy to read."
  ];
  return (
    <div className="help-center">
      <section className="wide-panel">
        <h2><CircleHelp size={16} /> What does this app do?</h2>
        <p className="muted">It turns local media into an editable JSON timeline, lets AI propose edits for review, previews the result, then exports through FFmpeg. Advanced users can still open the raw JSON and logs.</p>
        <div className="button-grid compact">
          <button onClick={onOpenDocs}><CircleHelp size={16} /> Open bundled local docs</button>
          <button onClick={onOpenShortcuts}><Keyboard size={16} /> Keyboard shortcuts</button>
        </div>
      </section>
      <section className="wide-panel">
        <h2><Sparkles size={16} /> Example prompts</h2>
        <div className="example-prompt-grid">
          {prompts.map((item) => <span key={item}>{item}</span>)}
        </div>
      </section>
      <section className="wide-panel">
        <h2><Wand2 size={16} /> Beginner tips</h2>
        <div className="tip-card-grid">
          <span><strong>Start simple</strong> Import one video, choose Quick Create, then preview.</span>
          <span><strong>Review before applying</strong> AI plans show scenes and captions before changing the timeline.</span>
          <span><strong>Export last</strong> Use preview first, then run preflight before final render.</span>
          <span><strong>Advanced tools stay available</strong> JSON, logs, and diagnostics live under Advanced/Logs.</span>
        </div>
      </section>
    </div>
  );
}
