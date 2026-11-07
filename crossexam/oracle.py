"""Specification model. Recompute stock from an event ledger, not mutable balances.

This is maintained by the benchmark owner and never sent to either model or
mounted into the candidate process. It is still an oracle assumption, not a
formal proof that the English contract is correct.
"""


def evaluate(actions):
    reservations = []
    released = set()
    outputs = []
    for a in actions:
        op, tenant = a.get("op"), a.get("tenant")
        sku, qty, key = a.get("sku"), a.get("qty"), a.get("key")
        valid_tenant = isinstance(tenant, str) and bool(tenant)
        valid_key = isinstance(key, str) and bool(key)
        valid_sku = sku in ("widget", "sensor")
        if not valid_tenant or op not in ("stock", "reserve", "release"):
            outputs.append({"error": "invalid"})
            continue

        def available(t, s):
            return 10 - sum(r["qty"] for i, r in enumerate(reservations)
                            if i not in released and r["tenant"] == t and r["sku"] == s)

        if op == "stock":
            outputs.append({"available": available(tenant, sku)} if valid_sku else {"error": "invalid"})
            continue
        if not valid_key or (op == "reserve" and (not valid_sku or type(qty) is not int or not 1 <= qty <= 10)):
            outputs.append({"error": "invalid"})
            continue
        previous = next(((i, r) for i, r in enumerate(reservations)
                         if r["tenant"] == tenant and r["key"] == key), None)
        if op == "release":
            if previous is None:
                outputs.append({"error": "not_found"})
            else:
                released.add(previous[0])
                outputs.append({"status": "released", "tenant": tenant, "key": key})
        elif previous:
            r = previous[1]
            outputs.append(r.copy() if (r["sku"], r["qty"]) == (sku, qty) else {"error": "conflict"})
        elif available(tenant, sku) < qty:
            outputs.append({"error": "insufficient"})
        else:
            r = {"status": "reserved", "tenant": tenant, "key": key, "sku": sku, "qty": qty}
            reservations.append(r)
            outputs.append(r.copy())
    return outputs
