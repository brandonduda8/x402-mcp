import { useEffect, useRef, useState } from "react";
import type { DensityMode } from "../types/api";

interface Command {
  id: string;
  label: string;
  action: () => void;
  keywords?: string;
}

interface CommandPaletteProps {
  open: boolean;
  onClose: () => void;
  onToggleDemo: () => void;
  onDensityChange: (mode: DensityMode) => void;
  onOpenWizard: () => void;
  onOpenSeller: () => void;
  vaultAddress: string | null;
  payToAddress: string | null;
}

export function CommandPalette({
  open,
  onClose,
  onToggleDemo,
  onDensityChange,
  onOpenWizard,
  onOpenSeller,
  vaultAddress,
  payToAddress,
}: CommandPaletteProps) {
  const [query, setQuery] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const commands: Command[] = [
    { id: "wizard", label: "Open Setup Wizard", action: () => { onOpenWizard(); onClose(); }, keywords: "setup first run" },
    { id: "seller", label: "Sell Something", action: () => { onOpenSeller(); onClose(); }, keywords: "seller revenue" },
    { id: "demo", label: "Toggle Demo Mode", action: () => { onToggleDemo(); onClose(); }, keywords: "demo fake data" },
    { id: "guided", label: "Switch to Guided Mode", action: () => { onDensityChange("guided"); onClose(); }, keywords: "density mode" },
    { id: "standard", label: "Switch to Standard Mode", action: () => { onDensityChange("standard"); onClose(); }, keywords: "density mode" },
    { id: "operator", label: "Switch to Operator Mode", action: () => { onDensityChange("operator"); onClose(); }, keywords: "density mode" },
    ...(vaultAddress ? [{
      id: "copy-vault",
      label: `Copy Vault Address: ${vaultAddress.slice(0, 10)}…`,
      action: () => { navigator.clipboard.writeText(vaultAddress); onClose(); },
      keywords: "address wallet",
    }] : []),
    ...(payToAddress ? [{
      id: "copy-payto",
      label: `Copy Pay-To Address: ${payToAddress.slice(0, 10)}…`,
      action: () => { navigator.clipboard.writeText(payToAddress); onClose(); },
      keywords: "address wallet",
    }] : []),
  ];

  const filtered = query
    ? commands.filter(
        (c) =>
          c.label.toLowerCase().includes(query.toLowerCase()) ||
          c.keywords?.toLowerCase().includes(query.toLowerCase()),
      )
    : commands;

  useEffect(() => {
    if (open) {
      setQuery("");
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [open]);

  if (!open) return null;

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0, 0, 0, 0.5)",
        display: "flex",
        alignItems: "flex-start",
        justifyContent: "center",
        paddingTop: "20vh",
        zIndex: 200,
      }}
      onClick={(e) => e.target === e.currentTarget && onClose()}
      role="dialog"
      aria-label="Command palette"
    >
      <div
        style={{
          background: "var(--color-panel)",
          border: "1px solid var(--color-border)",
          borderRadius: "12px",
          width: "460px",
          maxWidth: "90vw",
          overflow: "hidden",
        }}
      >
        <input
          ref={inputRef}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Type a command…"
          style={{
            width: "100%",
            background: "transparent",
            border: "none",
            borderBottom: "1px solid var(--color-border)",
            color: "var(--color-text)",
            padding: "14px 16px",
            fontSize: "14px",
            outline: "none",
          }}
          onKeyDown={(e) => {
            if (e.key === "Escape") onClose();
            if (e.key === "Enter" && filtered.length > 0) filtered[0].action();
          }}
          aria-label="Search commands"
        />
        <div style={{ maxHeight: "300px", overflow: "auto" }}>
          {filtered.map((cmd) => (
            <button
              key={cmd.id}
              onClick={cmd.action}
              style={{
                display: "block",
                width: "100%",
                textAlign: "left",
                background: "transparent",
                border: "none",
                color: "var(--color-text)",
                padding: "10px 16px",
                fontSize: "13px",
                cursor: "pointer",
                borderBottom: "1px solid var(--color-border)",
              }}
              onMouseEnter={(e) => (e.currentTarget.style.background = "var(--color-border)")}
              onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
            >
              {cmd.label}
            </button>
          ))}
          {filtered.length === 0 && (
            <div style={{ padding: "16px", color: "var(--color-text-muted)", textAlign: "center", fontSize: "13px" }}>
              No commands found
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
