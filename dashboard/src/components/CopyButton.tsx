import { useState } from "react";

interface CopyButtonProps {
  text: string;
  label?: string;
  children?: React.ReactNode;
}

export function CopyButton({ text, label = "Copy", children }: CopyButtonProps) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // Fallback for non-secure contexts
    }
  }

  return (
    <button
      onClick={handleCopy}
      title={label}
      aria-label={label}
      style={{
        background: "none",
        border: "none",
        color: copied ? "var(--color-green)" : "var(--color-text-muted)",
        cursor: "pointer",
        fontSize: "inherit",
        padding: "2px 4px",
        borderRadius: "4px",
        transition: "color 150ms ease-out",
      }}
    >
      {copied ? "\u2713" : children ?? "\u2398"}
    </button>
  );
}
