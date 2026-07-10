"""Doctor checks: validate config, connectivity, and balances for mission-control wizard.

Runnable standalone via `python -m app.doctor` or consumed via `GET /doctor`.
"""

from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.config import settings


@dataclass
class Check:
    id: str
    label: str
    passed: bool
    fix: str = ""
    detail: str = ""


@dataclass
class DoctorReport:
    checks: list[Check] = field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        return all(c.passed for c in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.all_passed,
            "checks": [
                {
                    "id": c.id,
                    "label": c.label,
                    "passed": c.passed,
                    "fix": c.fix,
                    "detail": c.detail,
                }
                for c in self.checks
            ],
        }


async def run_checks() -> DoctorReport:
    report = DoctorReport()

    # 1. Server reachable (self-check — always passes when called via HTTP)
    report.checks.append(
        Check(
            id="server_reachable",
            label="Server reachable",
            passed=True,
            detail=f"Listening on {settings.host}:{settings.port}",
        )
    )

    # 2. Receive wallet set
    has_pay_to = bool(settings.x402_pay_to_address)
    report.checks.append(
        Check(
            id="pay_to_address",
            label="Receive wallet set (X402_PAY_TO_ADDRESS)",
            passed=has_pay_to,
            fix="" if has_pay_to else 'echo "X402_PAY_TO_ADDRESS=0xYourAddress" >> .env',
            detail=settings.x402_pay_to_address or "not set",
        )
    )

    # 3. Vault key set (optional)
    has_buyer_key = bool(settings.evm_private_key)
    report.checks.append(
        Check(
            id="buyer_key",
            label="Vault key set (EVM_PRIVATE_KEY) — optional, for paying",
            passed=has_buyer_key,
            fix="" if has_buyer_key else "Optional: set EVM_PRIVATE_KEY in .env for testnet pay_and_fetch",
            detail="configured" if has_buyer_key else "not set (probe-only mode)",
        )
    )

    # 4. Facilitator reachable
    facilitator_ok = False
    facilitator_detail = ""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(settings.x402_facilitator_url)
            facilitator_ok = resp.status_code < 500
            facilitator_detail = f"HTTP {resp.status_code}"
    except Exception as exc:
        facilitator_detail = str(exc)
    report.checks.append(
        Check(
            id="facilitator",
            label="x402 facilitator reachable",
            passed=facilitator_ok,
            fix="" if facilitator_ok else f"Check X402_FACILITATOR_URL ({settings.x402_facilitator_url})",
            detail=facilitator_detail,
        )
    )

    # 5. Discovery URL reachable
    discovery_ok = False
    discovery_detail = ""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(settings.cdp_discovery_url, params={"limit": 1})
            discovery_ok = resp.status_code < 500
            discovery_detail = f"HTTP {resp.status_code}"
    except Exception as exc:
        discovery_detail = str(exc)
    report.checks.append(
        Check(
            id="discovery",
            label="CDP discovery reachable",
            passed=discovery_ok,
            fix="" if discovery_ok else f"Check CDP_DISCOVERY_URL ({settings.cdp_discovery_url})",
            detail=discovery_detail,
        )
    )

    # 6. Redis mode
    redis_mode = "redis" if settings.redis_url else "memory"
    report.checks.append(
        Check(
            id="redis_mode",
            label="Store mode",
            passed=True,  # informational
            detail=redis_mode,
            fix="Set REDIS_URL for persistent storage" if redis_mode == "memory" else "",
        )
    )

    # 7. Network config
    report.checks.append(
        Check(
            id="network",
            label="Default network",
            passed=True,
            detail=settings.x402_default_network,
        )
    )

    # 8. Testnet USDC balance (if wallet configured)
    if has_buyer_key:
        balance_detail = await _read_vault_balance()
        report.checks.append(
            Check(
                id="testnet_funded",
                label="Testnet USDC funded",
                passed=balance_detail.get("funded", False),
                detail=balance_detail.get("detail", ""),
                fix=balance_detail.get("fix", ""),
            )
        )

    return report


async def _read_vault_balance() -> dict[str, Any]:
    """Read vault public address balance via public RPC. Never touches private key material."""
    try:
        from eth_account import Account

        account = Account.from_key(settings.evm_private_key)
        address = account.address
    except Exception as exc:
        return {"funded": False, "detail": f"Cannot derive address: {exc}", "fix": "Check EVM_PRIVATE_KEY format"}

    return await _check_usdc_balance(address)


async def _check_usdc_balance(address: str) -> dict[str, Any]:
    """Check USDC balance on Base Sepolia via public RPC."""
    # Base Sepolia USDC contract
    usdc_contract = "0x036CbD53842c5426634e7929541eC2318f3dCF7e"
    rpc_url = "https://sepolia.base.org"

    # ERC-20 balanceOf(address) selector
    padded = address.lower().replace("0x", "").zfill(64)
    data = f"0x70a08231{padded}"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                rpc_url,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "eth_call",
                    "params": [{"to": usdc_contract, "data": data}, "latest"],
                },
            )
            result = resp.json().get("result", "0x0")
            balance = int(result, 16)
            human = balance / 1_000_000
            funded = balance > 0
            fix = ""
            if not funded:
                fix = "Get testnet USDC from https://portal.cdp.coinbase.com/products/faucet"
            return {
                "funded": funded,
                "detail": f"{human:.6f} USDC ({balance} atomic) at {address}",
                "fix": fix,
                "balance_atomic": balance,
                "address": address,
            }
    except Exception as exc:
        return {"funded": False, "detail": f"RPC error: {exc}", "fix": "Check network connectivity"}


async def get_wallet_info() -> dict[str, Any]:
    """Public wallet info for GET /wallet — address and balances only. No key material."""
    address: str | None = None

    if settings.evm_private_key:
        try:
            from eth_account import Account

            account = Account.from_key(settings.evm_private_key)
            address = account.address
        except Exception:
            pass

    pay_to = settings.x402_pay_to_address

    result: dict[str, Any] = {
        "vault_address": address,
        "pay_to_address": pay_to,
        "network": settings.x402_default_network,
        "balances": {},
    }

    addresses_to_check: list[tuple[str, str]] = []
    if address:
        addresses_to_check.append(("vault", address))
    if pay_to and pay_to != address:
        addresses_to_check.append(("pay_to", pay_to))

    for label, addr in addresses_to_check:
        info = await _check_usdc_balance(addr)
        result["balances"][label] = {
            "address": addr,
            "usdc_atomic": info.get("balance_atomic", 0),
            "usdc_human": f"{info.get('balance_atomic', 0) / 1_000_000:.6f}",
            "funded": info.get("funded", False),
        }

    return result


def _cli_main() -> None:
    """Standalone: python -m app.doctor"""
    report = asyncio.run(run_checks())
    print("\nx402 Doctor Report")
    print("=" * 50)
    for check in report.checks:
        icon = "PASS" if check.passed else "FAIL"
        print(f"  [{icon}] {check.label}")
        if check.detail:
            print(f"         {check.detail}")
        if check.fix and not check.passed:
            print(f"         Fix: {check.fix}")
    print()
    if report.all_passed:
        print("All checks passed.")
    else:
        print("Some checks failed — see fixes above.")
        sys.exit(1)


if __name__ == "__main__":
    _cli_main()
