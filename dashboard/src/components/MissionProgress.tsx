import type { LedgerRow, StatsResponse } from "../types/api";

interface MissionProgressProps {
  stats: StatsResponse | null;
  spend: LedgerRow[];
  revenue: LedgerRow[];
  connected: boolean;
  density: string;
}

interface Step {
  id: string;
  label: string;
  passed: boolean;
}

export function MissionProgress({
  stats,
  spend,
  revenue,
  connected,
  density,
}: MissionProgressProps) {
  const config = stats?.config;
  const agents = stats?.agents ?? [];
  const totalCalls = agents.reduce((s, a) => s + a.calls_this_month, 0);
  const totalSpend = spend.reduce((s, r) => s + (r.amount_usdc ?? 0), 0);
  const totalRevenue = revenue.reduce((s, r) => s + (r.amount_usdc ?? 0), 0);
  const net = totalRevenue - totalSpend;

  const hasDiscovery = agents.some(
    (a) => a.agent_id.includes("scout") && a.calls_this_month > 0,
  );
  const hasProbe = totalCalls > 0;

  const steps: Step[] = [
    { id: "server", label: "Server up", passed: stats !== null },
    { id: "dashboard", label: "Dashboard connected", passed: connected },
    { id: "discovery", label: "First discovery", passed: hasDiscovery || totalCalls > 0 },
    { id: "probe", label: "First probe", passed: hasProbe },
    { id: "funded", label: "Testnet funded", passed: config?.has_buyer_key ?? false },
    { id: "paid_fetch", label: "First paid fetch", passed: spend.length > 0 },
    { id: "seller_config", label: "First seller config", passed: config?.has_pay_to ?? false },
    { id: "revenue", label: "First verified revenue", passed: revenue.length > 0 },
    { id: "net_positive", label: "Net >= 0", passed: net >= 0 && (spend.length > 0 || revenue.length > 0) },
  ];

  const completed = steps.filter((s) => s.passed).length;

  if (density === "operator") return null;

  return (
    <div className="panel" style={{ gridColumn: "span 6" }}>
      <div className="panel-title">
        Mission Progress
        {density === "guided" && (
          <span
            title="Track your journey from first clone to net-positive revenue."
            style={{ cursor: "help", opacity: 0.6 }}
          >
            ?
          </span>
        )}
        <span style={{ marginLeft: "auto", fontSize: "11px" }}>
          {completed}/{steps.length}
        </span>
      </div>

      {/* Compact progress bar */}
      <div
        style={{
          height: "4px",
          background: "var(--color-border)",
          borderRadius: "2px",
          overflow: "hidden",
          marginBottom: "12px",
        }}
      >
        <div
          style={{
            height: "100%",
            width: `${(completed / steps.length) * 100}%`,
            background: completed === steps.length ? "var(--color-green)" : "var(--color-usdc)",
            borderRadius: "2px",
            transition: "width 150ms ease-out",
          }}
        />
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
        {steps.map((step) => (
          <div
            key={step.id}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              fontSize: "12px",
              opacity: step.passed ? 1 : 0.6,
            }}
          >
            <span
              className={`dot ${step.passed ? "dot-green" : "dot-amber"}`}
              aria-hidden="true"
            />
            <span>{step.passed ? "Done" : "Todo"}: {step.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
