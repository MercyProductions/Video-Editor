import Editor, { type OnMount } from "@monaco-editor/react";

export function JsonEditor({
  text,
  schemaReady,
  onChange,
  onMount,
  validation
}: {
  text: string;
  schemaReady: boolean;
  onChange: (value: string) => void;
  onMount: OnMount;
  validation: EngineResult | null;
}) {
  return (
    <div className="editor-pane">
      <Editor
        height="100%"
        defaultLanguage="json"
        value={text}
        theme="vs-dark"
        loading="Loading Monaco..."
        options={{
          minimap: { enabled: false },
          fontSize: 14,
          wordWrap: "on",
          tabSize: 2,
          scrollBeyondLastLine: false,
          automaticLayout: true,
          formatOnPaste: true,
          formatOnType: true
        }}
        onMount={onMount}
        onChange={(value) => onChange(value || "")}
      />
      <div className="validation-strip">
        <span>{schemaReady ? "Schema validation active" : "Loading schema..."}</span>
        {validation && <span className={validation.ok ? "ok" : "error"}>{validation.ok ? "Valid JSON" : validation.stderr || validation.stdout}</span>}
      </div>
    </div>
  );
}
