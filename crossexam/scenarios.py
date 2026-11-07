"""Input-only test scenarios. Expected outputs belong exclusively to the oracle."""

import hashlib
import json
import random

FAMILIES = ("tenant_isolation", "idempotency", "payload_binding", "inventory", "validation")


def reserve(tenant="atlas", key="order-1", qty=2, sku="widget"):
    return dict(op="reserve", tenant=tenant, key=key, sku=sku, qty=qty)


def release(tenant="atlas", key="order-1"):
    return dict(op="release", tenant=tenant, key=key)


def stock(tenant="atlas", sku="widget"):
    return dict(op="stock", tenant=tenant, sku=sku)


def case(name, family, *actions):
    return dict(name=name, family=family, actions=list(actions))


def baseline():
    return [
        case("new reservation", "inventory", reserve(), stock()),
        case("release reservation", "inventory", reserve(), release(), stock()),
        case("insufficient inventory", "inventory", reserve(qty=6), reserve(key="order-2", qty=5)),
        case("independent products", "inventory", reserve(), reserve(key="other", sku="sensor"), stock(sku="sensor")),
    ]


def strengthened():
    """Documented hand-authored proposal for the reproducible offline demo."""
    return baseline() + [
        case("same key, different customers", "tenant_isolation", reserve(), reserve(tenant="beacon"), stock("beacon"), stock()),
        case("tenant spelling is significant", "tenant_isolation", reserve(tenant="Atlas"), reserve(), stock("Atlas"), stock()),
        case("tuple namespaces cannot collide", "tenant_isolation", reserve(tenant="a:b", key="c"), reserve(tenant="a", key="b:c")),
        case("tenant prefixes stay separate", "tenant_isolation", reserve(tenant="atlas-east"), reserve(tenant="atlas-west"), stock("atlas-west")),
        case("foreign release is invisible", "tenant_isolation", reserve(), release("beacon"), stock(), stock("beacon")),
        case("retry consumes no inventory", "idempotency", reserve(), reserve(), stock()),
        case("released keys retain their response", "idempotency", reserve(), release(), reserve(), stock()),
        case("quantity cannot change under a key", "payload_binding", reserve(), reserve(qty=3), stock()),
        case("product cannot change under a key", "payload_binding", reserve(), reserve(sku="sensor"), stock(sku="sensor")),
        case("release is idempotent", "inventory", reserve(), release(), release(), stock()),
        case("last unit can be reserved", "inventory", reserve(qty=10), stock()),
        case("each tenant owns its stock", "inventory", reserve(qty=8), reserve("beacon", qty=8), stock(), stock("beacon")),
        case("release restores the original product", "inventory", reserve(sku="sensor"), release(), stock(sku="sensor"), stock()),
        case("failed keys may recover", "idempotency", reserve(qty=8), reserve(key="retry", qty=4), release(), reserve(key="retry", qty=4), stock()),
        case("negative quantity is invalid", "validation", reserve(qty=-2), stock()),
        case("zero is invalid", "validation", reserve(qty=0), stock()),
        case("booleans are not quantities", "validation", reserve(qty=True), stock()),
        case("float quantities are invalid", "validation", reserve(qty=2.0), stock()),
        case("empty tenant is invalid", "validation", reserve(tenant="")),
        case("empty key is invalid", "validation", reserve(key="")),
        case("invalid retry cannot bypass validation", "validation", reserve(), reserve(qty=True)),
    ]


def audit_scenarios(seed=74519, count=32):
    """Fresh values and action sequences, independent from proposal generation."""
    rng = random.Random(seed)
    tests = []
    for i in range(count):
        tenant = f"org-{rng.randrange(100000)}"
        other = tenant + "-branch"
        key = f"request-{rng.randrange(100000)}"
        qty = rng.randint(1, 5)
        sku = rng.choice(["widget", "sensor"])
        actions = [reserve(tenant, key, qty, sku), reserve(other, key, qty, sku),
                   reserve(tenant, key, qty, sku), stock(tenant, sku),
                   reserve(tenant, key, qty + 1, sku), release(other, key),
                   release(tenant, key), release(tenant, key), stock(tenant, sku),
                   reserve(tenant, key, qty, sku), stock(tenant, sku)]
        tests.append(case(f"audit sequence {i + 1}", "mixed", *actions))
    return tests


def validate_suite(value):
    if not isinstance(value, list) or not 1 <= len(value) <= 80:
        raise ValueError("Suite must contain 1 to 80 scenarios")
    result = []
    for item in value:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str) or not item["name"] or len(item["name"]) > 160:
            raise ValueError("Each scenario needs a short name")
        if item.get("family") not in (*FAMILIES, "mixed"):
            raise ValueError("Unknown scenario family")
        actions = item.get("actions")
        if not isinstance(actions, list) or not 1 <= len(actions) <= 32 or not all(isinstance(a, dict) for a in actions):
            raise ValueError("Each scenario needs 1 to 32 action objects")
        # JSON only: the model never supplies executable test code or assertions.
        encoded = json.dumps(actions, allow_nan=False)
        if len(encoded) > 16000:
            raise ValueError("Scenario is too large")
        result.append(dict(name=item["name"], family=item["family"], actions=actions))
    return result


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
