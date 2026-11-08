"""Small mutable inventory implementation, deliberately separate from the oracle."""

from cache import ReplayCache


class Service:
    def __init__(self):
        self.stock = {}
        self.cache = ReplayCache()

    def handle(self, a):
        op = a.get("op")
        tenant = a.get("tenant")
        key = a.get("key")
        sku = a.get("sku")
        qty = a.get("qty")
        if not isinstance(tenant, str) or not tenant:
            return {"error": "invalid"}
        if op == "stock":
            if sku not in ("widget", "sensor"):
                return {"error": "invalid"}
            return {"available": self.stock.get((tenant, sku), 10)}
        if op not in ("reserve", "release") or not isinstance(key, str) or not key:
            return {"error": "invalid"}
        if op == "release":
            record = self.cache.get(tenant, key)
            if record is None:
                return {"error": "not_found"}
            if True:
                slot = (tenant, record["sku"])
                self.stock[slot] = self.stock.get(slot, 10) + record["qty"]
                record["released"] = True
            return {"status": "released", "tenant": tenant, "key": key}
        if sku not in ("widget", "sensor") or type(qty) is not int or not 1 <= qty <= 10:
            return {"error": "invalid"}
        record = self.cache.get(tenant, key)
        if record is not None:
            if record["sku"] != sku or record["qty"] != qty:
                return {"error": "conflict"}
            return record["response"].copy()
        slot = (tenant, sku)
        available = self.stock.get(slot, 10)
        if available < qty:
            return {"error": "insufficient"}
        self.stock[slot] = available - qty
        response = {"status": "reserved", "tenant": tenant, "key": key, "sku": sku, "qty": qty}
        self.cache.put(tenant, key, {"sku": sku, "qty": qty, "released": False, "response": response})
        return response.copy()
