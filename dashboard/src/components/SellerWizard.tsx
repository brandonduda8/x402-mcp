import { useState } from "react";

interface SellerWizardProps {
  open: boolean;
  onClose: () => void;
  defaultNetwork: string;
  payToAddress: string | null;
  dashboardActions: boolean;
  defaultPrice: string;
}

export function SellerWizard({
  open,
  onClose,
  defaultNetwork,
  payToAddress,
  dashboardActions,
  defaultPrice,
}: SellerWizardProps) {
  const [network, setNetwork] = useState(defaultNetwork);
  const [price, setPrice] = useState(defaultPrice);
  const [description, setDescription] = useState("Paid API access");
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [mainnetConfirm, setMainnetConfirm] = useState("");

  const isMainnet = network.includes("8453") && !network.includes("84532");
  const mainnetLocked = isMainnet && mainnetConfirm.toLowerCase() !== network;

  if (!open) return null;

  async function handleBuild() {
    setError(null);
    setResult(null);

    if (dashboardActions) {
      setLoading(true);
      try {
        const resp = await fetch("/seller/requirements", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ network, price, description }),
        });
        if (!resp.ok) {
          const body = await resp.json().catch(() => ({}));
          throw new Error(body.detail || `HTTP ${resp.status}`);
        }
        setResult(await resp.json());
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed");
      } finally {
        setLoading(false);
      }
    } else {
      // Show the MCP tool invocation
      setResult({
        _invocation: true,
        tool: "build_seller_requirements",
        params: { network, price, description, pay_to: payToAddress || "<your-address>" },
      });
    }
  }

  // Break-even math
  const priceNum = parseFloat(price.replace(/[^0-9.]/g, "")) || 0;
  const breakEvenCalls = priceNum > 0 ? Math.ceil(0.37 / priceNum) : 0;

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0, 0, 0, 0.7)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 100,
      }}
      onClick={(e) => e.target === e.currentTarget && onClose()}
      role="dialog"
      aria-label="Sell something wizard"
    >
      <div
        style={{
          background: "var(--color-panel)",
          border: "1px solid var(--color-border)",
          borderRadius: "12px",
          padding: "24px",
          maxWidth: "560px",
          width: "90vw",
          maxHeight: "80vh",
          overflow: "auto",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "16px" }}>
          <h2 style={{ fontSize: "16px", fontWeight: 600 }}>Sell Something</h2>
          <button onClick={onClose} style={closeBtnStyle} aria-label="Close">x</button>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
          <Field label="Price">
            <input
              value={price}
              onChange={(e) => setPrice(e.target.value)}
              style={inputStyle}
              placeholder="$0.01"
              aria-label="Price"
            />
          </Field>

          <Field label="Network">
            <select value={network} onChange={(e) => setNetwork(e.target.value)} style={inputStyle} aria-label="Network">
              <option value="eip155:84532">Base Sepolia (testnet)</option>
              <option value="eip155:8453">Base Mainnet (real money)</option>
            </select>
          </Field>

          {isMainnet && (
            <div style={{ padding: "10px", background: "rgba(229, 72, 77, 0.1)", borderRadius: "6px", fontSize: "13px" }}>
              <strong style={{ color: "var(--color-red)" }}>This spends real USDC on Base Mainnet.</strong>
              <div style={{ marginTop: "8px" }}>
                Type the network ID to confirm: <code className="mono" style={{ fontSize: "11px" }}>{network}</code>
              </div>
              <input
                value={mainnetConfirm}
                onChange={(e) => setMainnetConfirm(e.target.value)}
                placeholder={network}
                style={{ ...inputStyle, marginTop: "6px", fontSize: "12px" }}
                aria-label="Confirm mainnet network"
              />
            </div>
          )}

          <Field label="Description">
            <input
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              style={inputStyle}
              placeholder="Paid API access"
              aria-label="Description"
            />
          </Field>

          <button
            onClick={handleBuild}
            disabled={loading || mainnetLocked || !price}
            style={{
              ...btnStyle,
              opacity: loading || mainnetLocked ? 0.5 : 1,
            }}
          >
            {loading ? "Building…" : "Build Requirements"}
          </button>

          {priceNum > 0 && (
            <div style={{ fontSize: "12px", color: "var(--color-text-muted)" }}>
              At {price}/call, {breakEvenCalls} verified calls covers a typical month's spend.
            </div>
          )}
        </div>

        {error && (
          <div style={{ color: "var(--color-red)", fontSize: "13px", marginTop: "12px" }}>
            {error}
          </div>
        )}

        {result && (
          <div style={{ marginTop: "16px" }}>
            <div className="panel-title">
              {(result as Record<string, unknown>)._invocation ? "MCP Tool Invocation" : "Requirements JSON"}
            </div>
            <pre
              style={{
                background: "var(--color-base)",
                borderRadius: "6px",
                padding: "12px",
                fontSize: "11px",
                fontFamily: "var(--font-mono)",
                overflow: "auto",
                maxHeight: "200px",
                whiteSpace: "pre-wrap",
              }}
            >
              {JSON.stringify(result, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "13px" }}>
      <span style={{ color: "var(--color-text-muted)", fontWeight: 500 }}>{label}</span>
      {children}
    </label>
  );
}

const inputStyle: React.CSSProperties = {
  background: "var(--color-base)",
  border: "1px solid var(--color-border)",
  borderRadius: "6px",
  color: "var(--color-text)",
  padding: "8px 12px",
  fontSize: "13px",
};

const btnStyle: React.CSSProperties = {
  background: "var(--color-usdc)",
  border: "none",
  borderRadius: "6px",
  color: "white",
  padding: "10px 16px",
  fontSize: "14px",
  fontWeight: 500,
  cursor: "pointer",
};

const closeBtnStyle: React.CSSProperties = {
  background: "none",
  border: "none",
  color: "var(--color-text-muted)",
  fontSize: "18px",
  cursor: "pointer",
};
