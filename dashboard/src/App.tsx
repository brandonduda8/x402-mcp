import { useCallback, useEffect, useRef, useState } from "react";
import type { DensityMode } from "./types/api";
import { useStats, useLedger, useDoctor, useWallet } from "./hooks/useApi";
import { useSSE } from "./hooks/useSSE";
import { DEMO_EVENTS } from "./lib/demo-data";
import { downloadCsv } from "./lib/export";

import { Header } from "./components/Header";
import { PersistenceBanner } from "./components/PersistenceBanner";
import { NetPosition } from "./components/NetPosition";
import { QuotaGauge } from "./components/QuotaGauge";
import { RateSparkline } from "./components/RateSparkline";
import { ActivityStream } from "./components/ActivityStream";
import { AgentLanes } from "./components/AgentLanes";
import { LedgerTable } from "./components/LedgerTable";
import { Inspector } from "./components/Inspector";
import { Wizard } from "./components/Wizard";
import { WalletPanel } from "./components/WalletPanel";
import { MissionProgress } from "./components/MissionProgress";
import { SellerWizard } from "./components/SellerWizard";
import { CommandPalette } from "./components/CommandPalette";
import { ParallaxProtocolHero } from "./components/ParallaxProtocolHero";

function loadPersisted<T>(key: string, fallback: T): T {
  try {
    const val = localStorage.getItem(key);
    return val ? (JSON.parse(val) as T) : fallback;
  } catch {
    return fallback;
  }
}

export default function App() {
  const [demo, setDemo] = useState(() => loadPersisted("x402_demo", false));
  const [density, setDensity] = useState<DensityMode>(() =>
    loadPersisted("x402_density", "guided"),
  );
  const [wizardOpen, setWizardOpen] = useState(false);
  const [sellerOpen, setSellerOpen] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [restartToasted, setRestartToasted] = useState(false);

  const { data: stats, error: statsError } = useStats(demo);
  const { rows: spend } = useLedger("spend", demo);
  const { rows: revenue } = useLedger("revenue", demo);
  const { data: doctor } = useDoctor(demo);
  const { data: wallet } = useWallet(demo);
  const { events, status } = useSSE("", demo);

  // Merge demo events if in demo mode
  const allEvents = demo ? DEMO_EVENTS : events;

  // Persist settings
  useEffect(() => {
    localStorage.setItem("x402_demo", JSON.stringify(demo));
  }, [demo]);
  useEffect(() => {
    localStorage.setItem("x402_density", JSON.stringify(density));
  }, [density]);

  // Auto-open wizard on first run with failing checks
  useEffect(() => {
    if (doctor && !doctor.ok && !demo) {
      setWizardOpen(true);
    }
  }, [doctor, demo]);

  // cmd+K shortcut
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setPaletteOpen((prev) => !prev);
      }
      if (e.key === "Escape") {
        setPaletteOpen(false);
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  // Counter-reset detection: snap (no animation), toast once
  const prevTotalCalls = useRef<number | null>(null);
  useEffect(() => {
    if (!stats) return;
    const total = stats.agents.reduce((s, a) => s + a.calls_this_month, 0);
    if (prevTotalCalls.current !== null && total < prevTotalCalls.current && !restartToasted) {
      setRestartToasted(true);
      setTimeout(() => setRestartToasted(false), 8000);
    }
    prevTotalCalls.current = total;
  }, [stats, restartToasted]);

  const config = stats?.config;
  const agents = stats?.agents ?? [];
  const network = config?.network ?? "eip155:84532";
  const maxTier = agents.reduce(
    (best, a) => (a.tier === "pro" ? "pro" : best),
    "free",
  );
  const quota = config?.free_tier_monthly_quota ?? 500;
  const rateLimit = config?.free_tier_rate_limit_per_min ?? 10;
  const defaultPrice = config?.x402_default_price ?? "$0.01";

  const handleToggleDemo = useCallback(() => setDemo((d: boolean) => !d), []);

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <Header
        network={network}
        tier={maxTier}
        status={demo ? "connected" : status}
        demo={demo}
        onToggleDemo={handleToggleDemo}
        density={density}
        onDensityChange={setDensity}
        onOpenWizard={() => setWizardOpen(true)}
      />

      <PersistenceBanner
        redisMode={config?.redis_mode ?? "memory"}
        hasRevenue={revenue.length > 0}
      />

      {/* Restart toast */}
      {restartToasted && (
        <div className="banner banner-amber" role="alert">
          Server restarted — in-memory counters reset.
        </div>
      )}

      {/* Stats error */}
      {statsError && !demo && (
        <div className="banner banner-red" role="alert">
          <span className="dot dot-red" aria-hidden="true" />
          Dashboard can't reach the server at :8402 — is it running?{" "}
          <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>make up</code>
        </div>
      )}

      {/* 12-col grid layout */}
      <main
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(12, 1fr)",
          gap: "16px",
          padding: "16px 24px",
          flex: 1,
          overflow: "auto",
          alignContent: "start",
        }}
      >
        <div style={{ gridColumn: "span 12" }}>
          <ParallaxProtocolHero />
        </div>
        {/* Row 1: Stats */}
        <NetPosition
          spend={spend}
          revenue={revenue}
          defaultPrice={defaultPrice}
          density={density}
        />
        <QuotaGauge agents={agents} quota={quota} density={density} />
        <RateSparkline events={allEvents} rateLimit={rateLimit} density={density} />

        {/* Row 2: Activity + Agent lanes */}
        <ActivityStream events={allEvents} density={density} />
        <AgentLanes agents={agents} events={allEvents} density={density} />

        {/* Row 3: Ledger tables with CSV export */}
        <LedgerTable
          title="Spend Ledger"
          rows={spend}
          density={density}
          guidedHelp="USDC spent by your agents paying for x402 services."
          emptyMessage="Nothing spent. Good."
          emptyAction="Here's how to make your first $0.00 testnet fetch -->"
          onExport={() => downloadCsv(spend, "spend")}
        />
        <LedgerTable
          title="Revenue Ledger"
          rows={revenue}
          density={density}
          guidedHelp="USDC earned when external agents pay for your services."
          emptyMessage="No revenue yet"
          emptyAction="Set up a seller config to start earning"
          onExport={() => downloadCsv(revenue, "revenue")}
        />

        {/* Row 4: Wallet + Mission Progress */}
        <WalletPanel wallet={wallet} density={density} />
        <MissionProgress
          stats={stats}
          spend={spend}
          revenue={revenue}
          connected={status === "connected" || demo}
          density={density}
        />

        {/* Row 5: Inspector */}
        <Inspector density={density} demo={demo} />
      </main>

      {/* Demo watermark */}
      {demo && <div className="demo-watermark">DEMO</div>}

      {/* Setup wizard */}
      <Wizard
        checks={doctor?.checks ?? []}
        open={wizardOpen}
        onClose={() => setWizardOpen(false)}
      />

      {/* Seller wizard */}
      <SellerWizard
        open={sellerOpen}
        onClose={() => setSellerOpen(false)}
        defaultNetwork={network}
        payToAddress={wallet?.pay_to_address ?? null}
        dashboardActions={config?.dashboard_actions ?? false}
        defaultPrice={defaultPrice}
      />

      {/* cmd+K command palette */}
      <CommandPalette
        open={paletteOpen}
        onClose={() => setPaletteOpen(false)}
        onToggleDemo={handleToggleDemo}
        onDensityChange={setDensity}
        onOpenWizard={() => { setWizardOpen(true); setPaletteOpen(false); }}
        onOpenSeller={() => { setSellerOpen(true); setPaletteOpen(false); }}
        vaultAddress={wallet?.vault_address ?? null}
        payToAddress={wallet?.pay_to_address ?? null}
      />
    </div>
  );
}
