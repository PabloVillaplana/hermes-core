#!/usr/bin/env python3
"""Hermes pre_tool_call hook: block purchases, payments and payment-card handling.

Installed to ~/.hermes/agent-hooks/financial-guard.py by hermes-core/scripts/install.sh and
declared in every profile's config.yaml with fail_closed: true, so a crash also blocks.

Protocol (Hermes shell hooks): JSON payload on stdin, JSON directive on stdout.
  {"action": "block", "message": "..."}    -> tool call is refused, message goes to the model
  {"action": "approve", "message": "..."}  -> escalated to Villa's approval prompt
  {}                                       -> allowed

Standard library only. Keep it fast: it runs before every tool call.
"""
import json
import re
import sys

BLOCK_PREFIX = "FINANCIAL GUARD: "
POLICY = (
    " Agents in Villa's Hermes profiles must never buy, pay, transfer money, subscribe, "
    "or handle payment-card data. Stop and tell Villa what you were trying to do; he will do it himself."
)

# ---------------------------------------------------------------------------
# Payment cards
# ---------------------------------------------------------------------------

# 13-19 digits, contiguous or in groups separated by single spaces/dashes.
CARD_CANDIDATE = re.compile(r"(?<![\d.])(?:\d[ -]?){12,18}\d(?![\d.])")

# Major network prefixes (IIN ranges), checked on the normalized number.
NETWORK = re.compile(
    r"^(?:4\d{12}(?:\d{3}){0,2}"            # Visa 13/16/19
    r"|5[1-5]\d{14}"                         # Mastercard
    r"|2(?:2[2-9][1-9]|[3-6]\d\d|7[01]\d|720)\d{12}"  # Mastercard 2-series
    r"|3[47]\d{13}"                          # Amex
    r"|3(?:0[0-5]|[68]\d)\d{11,16}"          # Diners
    r"|6(?:011|5\d\d|4[4-9]\d)\d{12,15}"     # Discover
    r"|35(?:2[89]|[3-8]\d)\d{12,15}"         # JCB
    r"|62\d{14,17})$"                        # UnionPay
)

# Published sandbox numbers (Stripe, Braintree, Adyen, PayPal docs). Allowed so test suites and
# docs such as bmls.local/docs/stripe-test-cards.md can still be edited.
TEST_CARDS = {
    "4242424242424242", "4000056655665556", "5555555555554444", "2223003122003222",
    "5200828282828210", "5105105105105100", "378282246310005", "371449635398431",
    "6011111111111117", "6011000990139424", "6011981111111113", "3056930009020004",
    "36227206271667", "3566002020360505", "6200000000000005", "6200000000000047",
    "4111111111111111", "4012888888881881", "4222222222222", "5431111111111111",
    "4005519200000004", "4009348888881881", "4012000033330026", "4012000077777777",
    "4217651111111119", "4500600000000061", "6011000991300009", "3530111333300000",
    "378734493671000", "5610591081018250", "30569309025904", "38520000023237",
}


def luhn_ok(number: str) -> bool:
    total, alt = 0, False
    for ch in reversed(number):
        d = ord(ch) - 48
        if alt:
            d *= 2
            if d > 9:
                d -= 9
        total += d
        alt = not alt
    return total % 10 == 0


def is_test_card(number: str) -> bool:
    # Stripe's documented test ranges are 4000 00xx xxxx xxxx and numbers with long zero runs.
    return number in TEST_CARDS or number.startswith("400000") or "0000000" in number


def find_real_cards(text: str):
    for m in CARD_CANDIDATE.finditer(text):
        raw = m.group(0)
        # Groups must be uniform: either no separators or one consistent separator style.
        if " " in raw and "-" in raw:
            continue
        number = re.sub(r"[ -]", "", raw)
        if NETWORK.match(number) and luhn_ok(number) and not is_test_card(number):
            yield m.start(), number


CARD_CONTEXT = re.compile(
    r"card|tarjeta|\bcc\b|cc[_-]?num|\bpan\b|visa|master ?card|amex|american express|discover|"
    r"cvv|cvc|expir|venc|billing|payment|pago",
    re.I,
)
CVV = re.compile(
    r"(?:cvv2?|cvc2?|card verification|security code|c[oó]digo de seguridad)\W{0,12}\d{3,4}\b", re.I
)
LIVE_SECRET = re.compile(r"\b(?:sk|rk)_live_[0-9A-Za-z]{8,}")

# ---------------------------------------------------------------------------
# Tool classification
# ---------------------------------------------------------------------------

FILE_TOOLS = re.compile(r"^(?:write_file|patch|edit_file|str_replace|create_file|notebook_edit)$")
READ_ONLY_TOOLS = re.compile(r"^(?:read_file|list_dir|search_files|grep|glob|session_search|memory_search)$")

# Composio / other SaaS action slugs, e.g. STRIPE_CREATE_PAYMENT_INTENT, SHOPIFY_CREATE_ORDER.
FINANCIAL_TOOLKITS = (
    "STRIPE PAYPAL SQUARE SQUAREUP BRAINTREE ADYEN CHECKOUT WISE TRANSFERWISE REVOLUT COINBASE "
    "BINANCE KRAKEN PLAID MERCURY BREX RAMP VENMO CASHAPP ZELLE RAZORPAY MERCADOPAGO MERCADO_PAGO "
    "PAYONEER KLARNA AFFIRM CHARGEBEE PADDLE LEMONSQUEEZY LEMON_SQUEEZY GUMROAD RECURLY "
    "SHOPIFY WOOCOMMERCE BIGCOMMERCE AMAZON EBAY ETSY ALIEXPRESS INSTACART DOORDASH UBER UBEREATS "
    "EXPEDIA BOOKING AIRBNB GODADDY NAMECHEAP PORKBUN DYNADOT GANDI HOVER TICKETMASTER EVENTBRITE "
    "QUICKBOOKS XERO FRESHBOOKS BILL BILLCOM BANK BAC BCR BNCR SINPE"
).split()
READ_VERBS = re.compile(
    r"_(?:LIST|GET|RETRIEVE|SEARCH|FETCH|FIND|DESCRIBE|COUNT|READ|SHOW|LOOKUP|QUERY|VIEW|PREVIEW)(?:_|$)"
)
MONEY_ACTIONS = re.compile(
    r"(?:^|_)(?:PURCHASE|CHECKOUT|BUY|PLACE_ORDER|SUBMIT_ORDER|CREATE_ORDER|CONFIRM_ORDER|"
    r"CREATE_CHARGE|CAPTURE_CHARGE|CREATE_PAYMENT|CONFIRM_PAYMENT|CAPTURE_PAYMENT|SEND_PAYMENT|"
    r"MAKE_PAYMENT|PAY|PAY_INVOICE|PAYOUT|CREATE_PAYOUT|TRANSFER_FUNDS|CREATE_TRANSFER|SEND_MONEY|"
    r"WIRE|CREATE_REFUND|REFUND|CREATE_SUBSCRIPTION|UPDATE_SUBSCRIPTION|SUBSCRIBE|UPGRADE_PLAN|"
    r"CHANGE_PLAN|ADD_PAYMENT_METHOD|ATTACH_PAYMENT_METHOD|ADD_CARD|CREATE_CARD|ISSUE_CARD|"
    r"REGISTER_DOMAIN|RENEW_DOMAIN|TRANSFER_DOMAIN|TOP_UP|TOPUP|ADD_FUNDS|REDEEM|DONATE|TIP)(?:_|$)"
)

# URLs a browser (or `open` in the terminal) must not reach.
BLOCK_URL = re.compile(
    r"https?://[^\s\"']*(?:checkout|/cart\b|/basket\b|/buy\b|/buy[-_/]|/purchase|/pay\b|/pay/|/payment|"
    r"/order/confirm|/place-?order|/subscribe|/donate|/topup|/top-up)"
    r"|https?://(?:[a-z0-9-]+\.)*(?:paypal\.com|pay\.google\.com|checkout\.stripe\.com|buy\.stripe\.com|"
    r"billing\.stripe\.com|pay\.amazon\.com|venmo\.com|cash\.app|wise\.com/send|revolut\.me|"
    r"paddle\.com/checkout|gumroad\.com/l/|lemonsqueezy\.com/checkout|shop\.app)",
    re.I,
)
URL = re.compile(r"https?://[^\s\"'<>]+", re.I)
DOCS_HOST = re.compile(r"https?://(?:docs|developer|developers|dev|support|help|status|stripe\.dev)\.", re.I)
APPROVE_URL = re.compile(
    r"https?://[^\s\"']*(?:/billing|/upgrade|/pricing/select|/plans?/(?:change|upgrade)|/account/subscription|"
    r"/settings/billing|/wallet)",
    re.I,
)

# Terminal commands that spend money or move it.
TERMINAL_BLOCK = [
    (re.compile(r"\bstripe\b[^\n|;&]*--live\b"), "Stripe CLI in live mode"),
    (re.compile(r"\b(?:vercel|vc)\s+domains?\s+(?:buy|purchase|transfer-in)\b"), "buying a domain"),
    (re.compile(r"\baws\s+route53domains\s+(?:register|renew|transfer)-domain\b"), "registering a domain"),
    (re.compile(r"\bgcloud\s+domains\s+registrations\s+(?:register|renew|transfer)\b"), "registering a domain"),
    (re.compile(r"\baws\s+ec2\s+purchase-"), "purchasing AWS reservations"),
    (re.compile(r"\baws\s+savingsplans\s+create-savings-plan\b"), "buying an AWS savings plan"),
    (re.compile(r"\baws\s+marketplace-\S+\s+(?:subscribe|create-agreement)"), "AWS Marketplace purchase"),
    (re.compile(r"\baz\s+reservations\s+reservation-order\s+purchase\b"), "Azure reservation purchase"),
    (re.compile(r"\bmas\s+(?:purchase|install)\b"), "Mac App Store purchase"),
    (re.compile(r"\bgh\s+api\b[^\n]*marketplace_listing/(?:plans|accounts)[^\n]*-X\s*(?:POST|PUT)", re.I),
     "GitHub Marketplace purchase"),
    (re.compile(r"api-m\.paypal\.com|api\.paypal\.com"), "PayPal live API"),
    (re.compile(r"\bopen\s+['\"]?https?://", re.I), None),  # handled by URL rules below
]
PAYMENT_API = re.compile(
    r"https?://(?:api\.stripe\.com|api\.squareup\.com|api\.braintreegateway\.com|checkout-live\.adyen\.com|"
    r"pal-live\.adyen\.com|api\.wise\.com|api\.transferwise\.com|b2b\.revolut\.com|api\.coinbase\.com|"
    r"api\.mercury\.com|api\.brex\.com|production\.plaid\.com|api\.mercadopago\.com)",
    re.I,
)
WRITE_HTTP = re.compile(r"(?:-X\s*(?:POST|PUT|PATCH|DELETE)\b|--request\s+(?:POST|PUT|PATCH|DELETE)\b|"
                        r"\s-d\s|\s--data|\s-F\s|--form\b|\bhttp\s+(?:POST|PUT|PATCH)\b|requests\.post|fetch\()",
                        re.I)


ACTION_KEYS = {"tool_slug", "tool_slugs", "slug", "slugs", "action", "actions", "action_name", "tool", "tools",
               "tool_name", "tool_names"}
TOOLKIT_KEYS = {"toolkit", "toolkits", "toolkit_slug", "toolkit_slugs", "app", "apps", "app_name", "app_names",
                "integration", "integrations"}


def collect(obj, keys, out=None):
    """Recursively collect string values stored under the given keys."""
    if out is None:
        out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if str(k).lower() in keys:
                if isinstance(v, str):
                    out.append(v)
                elif isinstance(v, list):
                    out.extend(x for x in v if isinstance(x, str))
            collect(v, keys, out)
    elif isinstance(obj, list):
        for x in obj:
            collect(x, keys, out)
    return out


def block(reason: str) -> dict:
    return {"action": "block", "message": BLOCK_PREFIX + reason + "." + POLICY}


def approve(reason: str) -> dict:
    return {"action": "approve", "message": BLOCK_PREFIX + reason + ". Villa must approve this explicitly.",
            "rule_key": "financial-guard"}


def check(tool_name: str, tool_input) -> dict:
    tool = (tool_name or "").strip()
    tool_l = tool.lower()
    text = json.dumps(tool_input, ensure_ascii=False) if not isinstance(tool_input, str) else tool_input

    if READ_ONLY_TOOLS.match(tool_l):
        return {}

    # 1. Live payment secrets never pass through the agent, in any tool.
    if LIVE_SECRET.search(text):
        return block("a live payment secret key (sk_live_/rk_live_) appears in this tool call")

    is_file_write = bool(FILE_TOOLS.match(tool_l))

    # 2. Real payment card numbers.
    for pos, _ in find_real_cards(text):
        if is_file_write:
            window = text[max(0, pos - 80): pos + 80]
            if not CARD_CONTEXT.search(window):
                continue  # a long numeric id in code, not a card
        return block("this tool call contains what looks like a real payment card number")

    # 3. CVV / security codes outside source files.
    if not is_file_write and CVV.search(text):
        return block("this tool call contains a card security code")

    if is_file_write:
        return {}

    # 4. Saved payment cards in the Hermes vault.
    if tool_l == "browser_vault":
        action = str((tool_input or {}).get("action", "")).lower() if isinstance(tool_input, dict) else ""
        if action not in ("", "list") and re.search(r"card|payment|tarjeta|visa|master|amex|cc", text, re.I):
            return block("filling a saved payment card is not allowed")
        if action == "fill":
            return approve("the agent wants to fill a saved vault item; confirm it is a LOGIN, not a card")

    # 5. Browser / terminal navigation to checkout or payment pages (documentation sites are fine).
    for url in URL.findall(text):
        if DOCS_HOST.match(url):
            continue
        if BLOCK_URL.search(url):
            return block("opening a checkout, cart or payment page is not allowed")

    # 6. SaaS actions (Composio and other MCP tools). Only action identifiers are inspected,
    #    never free text, so a Jira comment that mentions "STRIPE_SECRET_KEY" is fine.
    if "mcp" in tool_l or "composio" in tool_l:
        names = [tool.upper()] + [v.upper() for v in collect(tool_input, ACTION_KEYS)]
        for name in names:
            segments = [seg for seg in re.split(r"[^A-Z0-9]+", name) if seg]
            joined = "_".join(segments)
            is_read = bool(READ_VERBS.search("_" + joined + "_"))
            if MONEY_ACTIONS.search(joined) and not is_read:
                return block(f"the action {name} would buy, pay, transfer or subscribe")
            fin = next((seg for seg in segments[:4] if seg in FINANCIAL_TOOLKITS), None)
            if fin and not is_read:
                return block(f"write actions on the financial/commerce app {fin.title()} are not allowed ({name})")
        for app in collect(tool_input, TOOLKIT_KEYS):
            if app.upper().replace("-", "_") in FINANCIAL_TOOLKITS or app.upper() in FINANCIAL_TOOLKITS:
                return block(f"connecting or using the financial/commerce app {app} is not allowed")

    # 7. Terminal commands.
    if tool_l in ("terminal", "bash", "shell", "execute_code", "run_command", "process"):
        cmd = text
        for pattern, reason in TERMINAL_BLOCK:
            if reason and pattern.search(cmd):
                return block(reason + " is not allowed")
        if PAYMENT_API.search(cmd) and WRITE_HTTP.search(cmd):
            if "sk_test_" in cmd or "sandbox" in cmd.lower():
                return {}
            return block("write calls to a payment provider API are not allowed outside test/sandbox mode")
        if any(APPROVE_URL.search(u) for u in URL.findall(cmd) if not DOCS_HOST.match(u)):
            return approve("opening a billing or plan page")

    if tool_l.startswith("browser") and any(APPROVE_URL.search(u) for u in URL.findall(text) if not DOCS_HOST.match(u)):
        return approve("opening a billing or plan page")

    return {}


def main() -> int:
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        print(json.dumps(block("the hook received an unreadable payload")))
        return 0
    decision = check(payload.get("tool_name") or "", payload.get("tool_input"))
    print(json.dumps(decision))
    return 0


if __name__ == "__main__":
    sys.exit(main())
