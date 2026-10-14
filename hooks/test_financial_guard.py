#!/usr/bin/env python3
"""Tests for financial-guard.py. Run: python3 hermes-core/hooks/test_financial_guard.py"""
import importlib.util
import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("guard", HERE / "financial-guard.py")
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)

REAL_VISA = "4532015112830366"      # Luhn-valid, not a published test card
REAL_MC_SPACED = "5425 2334 3010 9903"
REAL_AMEX = "348283432013921"

BLOCK, APPROVE, ALLOW = "block", "approve", "allow"

CASES = [
    # --- cards -------------------------------------------------------------------------------
    (BLOCK, "browser_type", {"ref": "e12", "text": REAL_VISA}),
    (BLOCK, "send_message", {"to": "x", "text": f"Card: {REAL_MC_SPACED}, exp 10/29"}),
    (BLOCK, "terminal", {"command": f"echo {REAL_AMEX}"}),
    (BLOCK, "write_file", {"path": "notes.md", "content": f"Customer card number {REAL_VISA}"}),
    (BLOCK, "browser_type", {"ref": "e3", "text": "CVV: 123"}),
    (ALLOW, "write_file", {"path": "tests/StripeTest.php", "content": "'card' => '4242424242424242', 'cvc' => '123'"}),
    (ALLOW, "write_file", {"path": "docs/stripe-test-cards.md", "content": "Decline: 4000 0000 0000 0002"}),
    (ALLOW, "write_file", {"path": "src/ids.ts", "content": "const ORDER_ID = 4532015112830366; // legacy id"}),
    (ALLOW, "terminal", {"command": "git log --since=1697000000000"}),
    (ALLOW, "read_file", {"path": "x", "content": REAL_VISA}),
    # --- live keys ---------------------------------------------------------------------------
    (BLOCK, "write_file", {"path": ".env", "content": "STRIPE_SECRET_KEY=sk_live_51Hxxxxxxxxxxxxxxxx"}),
    (ALLOW, "write_file", {"path": ".env.example", "content": "STRIPE_SECRET_KEY=sk_test_xxx"}),
    # --- vault -------------------------------------------------------------------------------
    (BLOCK, "browser_vault", {"action": "fill", "handle": "visa-personal-card"}),
    (APPROVE, "browser_vault", {"action": "fill", "handle": "h_7f2a"}),
    (ALLOW, "browser_vault", {"action": "list"}),
    # --- browser -----------------------------------------------------------------------------
    (BLOCK, "browser_navigate", {"url": "https://www.amazon.com/gp/buy/spc/handlers/display.html"}),
    (BLOCK, "browser_navigate", {"url": "https://shop.example.com/checkout/step-2"}),
    (BLOCK, "browser_navigate", {"url": "https://www.paypal.com/myaccount/transfer"}),
    (BLOCK, "browser_navigate", {"url": "https://buy.stripe.com/test_abc"}),
    (APPROVE, "browser_navigate", {"url": "https://github.com/settings/billing"}),
    (ALLOW, "browser_navigate", {"url": "https://docs.github.com/en/billing/managing-your-billing"}),
    (ALLOW, "browser_navigate", {"url": "https://percy.atlassian.net/browse/DEV-8180"}),
    (ALLOW, "browser_navigate", {"url": "https://docs.stripe.com/payments/accept-a-payment"}),
    (ALLOW, "browser_navigate", {"url": "https://developer.paypal.com/docs/checkout/"}),
    (BLOCK, "browser_navigate", {"url": "https://www.paypal.com/checkoutnow?token=x"}),
    # --- Composio / MCP ------------------------------------------------------------------------
    (BLOCK, "mcp_composio_COMPOSIO_MULTI_EXECUTE_TOOL",
     {"tools": [{"tool_slug": "STRIPE_CREATE_PAYMENT_INTENT", "arguments": {"amount": 1000}}]}),
    (BLOCK, "mcp_composio_COMPOSIO_MULTI_EXECUTE_TOOL",
     {"tools": [{"tool_slug": "SHOPIFY_CREATE_ORDER", "arguments": {}}]}),
    (BLOCK, "mcp_composio_COMPOSIO_MULTI_EXECUTE_TOOL",
     {"tools": [{"tool_slug": "PAYPAL_SEND_PAYOUT", "arguments": {}}]}),
    (BLOCK, "mcp_composio_COMPOSIO_MULTI_EXECUTE_TOOL",
     {"tools": [{"tool_slug": "AMAZON_ADD_TO_CART", "arguments": {}}]}),
    (BLOCK, "mcp_composio_COMPOSIO_MANAGE_CONNECTIONS", {"toolkits": ["stripe"], "action": "add"}),
    (BLOCK, "mcp_stripe_create_refund", {"charge": "ch_123"}),
    (ALLOW, "mcp_composio_COMPOSIO_MULTI_EXECUTE_TOOL",
     {"tools": [{"tool_slug": "STRIPE_LIST_CHARGES", "arguments": {"limit": 10}}]}),
    (ALLOW, "mcp_composio_COMPOSIO_MULTI_EXECUTE_TOOL",
     {"tools": [{"tool_slug": "JIRA_ADD_COMMENT",
                 "arguments": {"issue": "DEV-8180", "body": "Rotated STRIPE_SECRET_KEY; payment flow now retries"}}]}),
    (ALLOW, "mcp_composio_COMPOSIO_MULTI_EXECUTE_TOOL",
     {"tools": [{"tool_slug": "GITHUB_LIST_PULL_REQUESTS", "arguments": {"owner": "gitMLS"}}]}),
    (ALLOW, "mcp_composio_COMPOSIO_SEARCH_TOOLS", {"queries": [{"use_case": "find jira issues assigned to me"}]}),
    (ALLOW, "mcp_composio_COMPOSIO_MANAGE_CONNECTIONS", {"toolkits": ["jira", "github"]}),
    # --- terminal ------------------------------------------------------------------------------
    (BLOCK, "terminal", {"command": "stripe charges create --amount 2000 --live"}),
    (BLOCK, "terminal", {"command": "vercel domains buy example.com"}),
    (BLOCK, "terminal", {"command": "aws route53domains register-domain --domain-name x.com"}),
    (BLOCK, "terminal", {"command": "curl -X POST https://api.stripe.com/v1/charges -u $KEY: -d amount=100"}),
    (BLOCK, "terminal", {"command": "open 'https://shop.example.com/cart'"}),
    (ALLOW, "terminal", {"command": "stripe listen --forward-to localhost:3001/api/stripe/webhook"}),
    (ALLOW, "terminal", {"command": "curl -X POST https://api.stripe.com/v1/customers -u sk_test_abc: -d email=a@b.c"}),
    (ALLOW, "terminal", {"command": "curl -s https://api.stripe.com/v1/charges -u $KEY:"}),
    (ALLOW, "terminal", {"command": "vendor/bin/phpunit tests/controllers/Stripe_webhookTest.php"}),
    (ALLOW, "terminal", {"command": "claude -p \"Implement DEV-8180: fix the payment retry banner\" --permission-mode plan"}),
    (ALLOW, "terminal", {"command": "pnpm --filter dashboard stripe:listen"}),
    (ALLOW, "patch", {"path": "application/controllers/Stripe_webhook.php", "old": "a", "new": "b"}),
]


def outcome(decision: dict) -> str:
    return decision.get("action", "allow") if decision else "allow"


def main() -> int:
    failures = 0
    for expected, tool, args in CASES:
        got = outcome(guard.check(tool, args))
        if got != expected:
            failures += 1
            print(f"FAIL expected={expected} got={got} tool={tool} args={json.dumps(args)[:140]}")
    # End-to-end through stdin/stdout, as Hermes calls it.
    proc = subprocess.run([sys.executable, str(HERE / "financial-guard.py")],
                          input=json.dumps({"hook_event_name": "pre_tool_call", "tool_name": "browser_type",
                                            "tool_input": {"text": REAL_VISA}}),
                          capture_output=True, text=True, timeout=10)
    if json.loads(proc.stdout).get("action") != "block":
        failures += 1
        print("FAIL end-to-end stdin/stdout:", proc.stdout, proc.stderr)
    proc = subprocess.run([sys.executable, str(HERE / "financial-guard.py")], input="not json",
                          capture_output=True, text=True, timeout=10)
    if json.loads(proc.stdout).get("action") != "block":
        failures += 1
        print("FAIL malformed payload must block:", proc.stdout)
    total = len(CASES) + 2
    print(f"{total - failures}/{total} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
