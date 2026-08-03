"""Application configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    host: str = "0.0.0.0"
    port: int = 8402
    upgrade_url: str = "http://localhost:8402/upgrade"
    public_base_url: str = "http://localhost:8402"

    free_tier_monthly_quota: int = 500
    free_tier_rate_limit_per_min: int = 10
    pro_tier_monthly_quota: int = 50_000
    pro_tier_rate_limit_per_min: int = 120
    pro_tier_price: str = "$29.00"

    tool_credit_pack_size: int = 100
    tool_credit_pack_price: str = "$1.00"

    # Redis-ready: set REDIS_URL to migrate from in-memory stores.
    redis_url: str | None = None

    # Buyer (hot) — only used for pay_and_fetch spends. Never use cold receive key here.
    evm_private_key: str | None = None
    svm_private_key: str | None = None

    # Seller (cold receive) — on-chain payTo for revenue. Prefer separate from buyer.
    x402_pay_to_address: str | None = None

    # Dashboard actions: gated POST endpoints (seller wizard).
    dashboard_actions: bool = False

    # Extra CORS origins, comma-separated EXACT origins (scheme://host[:port]).
    # Set this to your tunnel origin when demoing; never a wildcard pattern.
    # A regex like https://.*.trycloudflare.com matches any tunnel anyone can
    # register for free, which is the same as allowing every origin against an
    # API that has no auth.
    cors_extra_origins: str = ""

    # Trust x-forwarded-host/proto when building public resource URLs. Only
    # enable behind a proxy you control — the value lands in the `resource` URL
    # baked into the signed 402 challenge and advertised to discovery catalogs.
    trust_forwarded_host: bool = False

    # How long a built PAYMENT-REQUIRED header is reused before rebuilding.
    challenge_cache_ttl_seconds: int = 300
    x402_facilitator_url: str = "https://x402.org/facilitator"
    x402_default_network: str = "eip155:84532"
    x402_default_price: str = "$0.01"

    # CDP Secret API keys (faucet + CDP facilitator auth for Bazaar indexing)
    cdp_api_key_id: str | None = None
    cdp_api_key_secret: str | None = None

    cdp_discovery_url: str = (
        "https://api.cdp.coinbase.com/platform/v2/x402/discovery/resources"
    )


settings = Settings()