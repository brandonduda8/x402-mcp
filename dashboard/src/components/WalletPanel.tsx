import type { WalletResponse } from "../types/api";
import { truncateHash } from "../lib/format";

interface WalletPanelProps {
  wallet: WalletResponse | null;
  density: string;
}

export function WalletPanel({ wallet, density }: WalletPanelProps) {
  if (!wallet) {
    return (
      <div className="panel" style={{ gridColumn: "span 6" }}>
        <div className="panel-title">Wallet</div>
        <div className="empty-state">
          <span>Loading wallet info…</span>
        </div>
      </div>
    );
  }

  const hasAnyAddress = wallet.vault_address || wallet.pay_to_address;

  return (
    <div className="panel" style={{ gridColumn: "span 6" }}>
      <div className="panel-title">
        Wallet
        {density === "guided" && (
          <span
            title="Public wallet addresses and balances. Private keys stay in your .env — never displayed here."
            style={{ cursor: "help", opacity: 0.6 }}
          >
            ?
          </span>
        )}
      </div>

      {!hasAnyAddress ? (
        <div className="empty-state">
          <span>No wallet configured</span>
          <span style={{ fontSize: "12px" }}>
            Set <code>X402_PAY_TO_ADDRESS</code> in .env to receive payments
          </span>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
          {wallet.vault_address && (
            <AddressRow
              label="Vault (buyer)"
              address={wallet.vault_address}
              balance={wallet.balances.vault}
              density={density}
            />
          )}
          {wallet.pay_to_address && (
            <AddressRow
              label="Pay-To (seller)"
              address={wallet.pay_to_address}
              balance={wallet.balances.pay_to}
              density={density}
            />
          )}
          <div style={{ fontSize: "11px", color: "var(--color-text-muted)", fontStyle: "italic" }}>
            Private keys stay in server .env — never displayed or transmitted.
          </div>
        </div>
      )}
    </div>
  );
}

function AddressRow({
  label,
  address,
  balance,
  density,
}: {
  label: string;
  address: string;
  balance?: { usdc_human: string; funded: boolean; usdc_atomic: number };
  density: string;
}) {
  const lowBalance = balance && !balance.funded;
  return (
    <div style={{ padding: "8px 10px", borderRadius: "6px", border: "1px solid var(--color-border)" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span style={{ fontSize: "12px", color: "var(--color-text-muted)" }}>{label}</span>
        {balance && (
          <span className="mono" style={{ fontSize: "13px", color: "var(--color-usdc)" }}>
            ${balance.usdc_human} USDC
          </span>
        )}
      </div>
      <div
        className="mono"
        style={{ fontSize: "12px", color: "var(--color-text)", marginTop: "4px" }}
        title={address}
      >
        {density === "operator" ? address : truncateHash(address, 8)}
      </div>
      {lowBalance && (
        <div style={{ fontSize: "11px", color: "var(--color-amber)", marginTop: "4px" }}>
          Low balance —{" "}
          <a
            href="https://portal.cdp.coinbase.com/products/faucet"
            target="_blank"
            rel="noopener noreferrer"
            style={{ color: "var(--color-amber)" }}
          >
            Get testnet USDC
          </a>
        </div>
      )}
    </div>
  );
}
