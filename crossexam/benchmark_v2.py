"""Contract faults for the 30-per-split revision; witnesses stay outside prompts."""


def extend(add):
    def v(n, title, family, filename, before, after):
        add(f"V{n:02d}", title, family, "validation", filename, before, after)

    def a(n, title, family, filename, before, after):
        add(f"A{n:02d}", title, family, "audit", filename, before, after)

    identity = "return (tenant, key)"
    replay = 'return record["response"].copy()'
    conflict = 'return {"error": "conflict"}'
    insufficient = 'return {"error": "insufficient"}'
    binding = 'if record["sku"] != sku or record["qty"] != qty:'
    restored = 'self.stock[slot] = self.stock.get(slot, 10) + record["qty"]'
    reserved = 'self.stock[slot] = available - qty'
    released = 'record["released"] = True'
    invalid_qty = 'if sku not in ("widget", "sensor") or type(qty) is not int or not 1 <= qty <= 10:'

    v(9, "Case-folded request keys collide", "tenant_isolation", "cache.py", identity, 'return (tenant, key.lower())')
    v(10, "Trimming tenant identity merges distinct customers", "tenant_isolation", "cache.py", identity, 'return (tenant.strip(), key)')
    v(11, "Truncated request keys alias distinct reservations", "tenant_isolation", "cache.py", identity, 'return (tenant, key[:8])')
    v(12, "Replay after release returns a changed status", "idempotency", "service.py", replay,
      'return {**record["response"], "status": "released"} if record["released"] else record["response"].copy()')
    v(13, "Cache retains only the most recent reservation", "idempotency", "cache.py",
      'self.entries[cache_key(tenant, key)] = record', 'self.entries.clear()\n        self.entries[cache_key(tenant, key)] = record')
    v(14, "Unknown release clears successful replay records", "idempotency", "service.py",
      'return {"error": "not_found"}', 'self.cache.entries.clear()\n                return {"error": "not_found"}')
    v(15, "Insufficient reservation poisons its retry key", "idempotency", "service.py", insufficient,
      'self.cache.put(tenant, key, {"sku": sku, "qty": qty, "released": False, "response": {"error": "insufficient"}})\n            return {"error": "insufficient"}')
    v(16, "Replay rewrites quantity to current availability", "idempotency", "service.py", replay,
      'return {**record["response"], "qty": self.stock.get((tenant, sku), 10)}')
    v(17, "Conflicting request deletes the successful key", "payload_binding", "service.py", conflict,
      'self.cache.entries.pop((tenant, key), None)\n                return {"error": "conflict"}')
    v(18, "Conflicting request silently consumes inventory", "payload_binding", "service.py", conflict,
      'self.stock[(tenant, sku)] = self.stock.get((tenant, sku), 10) - qty\n                return {"error": "conflict"}')
    v(19, "Released key bypasses payload binding", "payload_binding", "service.py", binding,
      'if not record["released"] and (record["sku"] != sku or record["qty"] != qty):')
    v(20, "Product conflict refunds an unreleased reservation", "payload_binding", "service.py", conflict,
      'if record["sku"] != sku:\n                    slot = (tenant, record["sku"])\n                    self.stock[slot] = self.stock.get(slot, 10) + record["qty"]\n                return {"error": "conflict"}')
    v(21, "Release always restores widget inventory", "inventory", "service.py",
      'slot = (tenant, record["sku"])', 'slot = (tenant, "widget")')
    v(22, "Release resets stock despite other live reservations", "inventory", "service.py", restored, 'self.stock[slot] = 10')
    v(23, "Sensor stock query reads the widget balance", "inventory", "service.py",
      'return {"available": self.stock.get((tenant, sku), 10)}', 'return {"available": self.stock.get((tenant, "widget"), 10)}')
    v(24, "Insufficient request debits stock before returning error", "inventory", "service.py", insufficient,
      'self.stock[slot] = available - qty\n            return {"error": "insufficient"}')
    v(25, "Maximum valid quantity is rejected", "validation", "service.py", 'not 1 <= qty <= 10', 'not 1 <= qty < 10')
    v(26, "Numeric strings coerced into valid quantities", "validation", "service.py", 'qty = a.get("qty")',
      'qty = a.get("qty")\n        if isinstance(qty, str) and qty.isdigit():\n            qty = int(qty)')
    v(27, "Missing tenant silently defaults to an existing customer", "validation", "service.py",
      'tenant = a.get("tenant")', 'tenant = a.get("tenant", "atlas")')
    v(28, "Unknown operation is interpreted as reserve", "validation", "service.py", 'op = a.get("op")',
      'op = a.get("op")\n        if op not in ("stock", "reserve", "release"):\n            op = "reserve"')
    v(29, "Stock queries accept unknown products", "validation", "service.py",
      'if sku not in ("widget", "sensor"):', 'if False:')
    v(30, "Release bypasses empty-key validation", "validation", "service.py",
      'or not isinstance(key, str) or not key:', 'or not isinstance(key, str) or (not key and op != "release"):')

    a(9, "Trimming request keys merges distinct reservations", "tenant_isolation", "cache.py", identity, 'return (tenant, key.strip())')
    a(10, "Tenant truncation merges organizations with a shared prefix", "tenant_isolation", "cache.py", identity, 'return (tenant[:8], key)')
    a(11, "Unseparated cache components create identity collisions", "tenant_isolation", "cache.py", identity, 'return tenant + key')
    a(12, "First replay evicts the key and breaks subsequent retries", "idempotency", "service.py", replay,
      'self.cache.entries.pop((tenant, key), None)\n            return record["response"].copy()')
    a(13, "Invalid request overwrites a successful replay record", "idempotency", "service.py", invalid_qty + '\n            return {"error": "invalid"}',
      invalid_qty + '\n            if self.cache.get(tenant, key) is not None:\n                self.cache.entries.pop((tenant, key), None)\n            return {"error": "invalid"}')
    a(14, "One release marks every reservation as already released", "idempotency", "service.py", released,
      'for entry in self.cache.entries.values():\n                    entry["released"] = True')
    a(15, "Replay adds live stock instead of returning the original response", "idempotency", "service.py", replay,
      'return {**record["response"], "available": self.stock.get((tenant, sku), 10)}')
    a(16, "Conflict requires both payload fields to change", "payload_binding", "service.py", binding,
      'if record["sku"] != sku and record["qty"] != qty:')
    a(17, "Rejected quantity conflict changes the later refund", "payload_binding", "service.py", conflict,
      'record["qty"] = qty\n                return {"error": "conflict"}')
    a(18, "Rejected product conflict changes the later refund bucket", "payload_binding", "service.py", conflict,
      'record["sku"] = sku\n                return {"error": "conflict"}')
    a(19, "Conflicting released keys incorrectly return not found", "payload_binding", "service.py", conflict,
      'return {"error": "not_found"} if record["released"] else {"error": "conflict"}')
    a(20, "First release refunds twice the reserved quantity", "inventory", "service.py", restored,
      'self.stock[slot] = self.stock.get(slot, 10) + 2 * record["qty"]')
    a(21, "Reservation debits one unit regardless of quantity", "inventory", "service.py", reserved, 'self.stock[slot] = available - 1')
    a(22, "Exact depletion leaves one phantom unit", "inventory", "service.py", reserved, 'self.stock[slot] = max(1, available - qty)')
    a(23, "Uninitialized stock query reports zero inventory", "inventory", "service.py",
      'return {"available": self.stock.get((tenant, sku), 10)}', 'return {"available": self.stock.get((tenant, sku), 0)}')
    a(24, "Sensor reservation also debits widget inventory", "inventory", "service.py", reserved,
      reserved + '\n        if sku == "sensor":\n            self.stock[(tenant, "widget")] = self.stock.get((tenant, "widget"), 10) - qty')
    a(25, "Minimum valid quantity is rejected", "validation", "service.py", 'not 1 <= qty <= 10', 'not 1 < qty <= 10')
    a(26, "Extra fields incorrectly invalidate otherwise valid actions", "validation", "service.py", 'op = a.get("op")',
      'if set(a) - {"op", "tenant", "key", "sku", "qty"}:\n            return {"error": "invalid"}\n        op = a.get("op")')
    a(27, "Numeric keys coerced into valid string identities", "validation", "service.py", 'key = a.get("key")',
      'key = a.get("key")\n        if isinstance(key, (int, float)):\n            key = str(key)')
    a(28, "Missing quantity silently defaults to one", "validation", "service.py", 'qty = a.get("qty")', 'qty = a.get("qty", 1)')
    a(29, "Stock observation wrongly requires an idempotency key", "validation", "service.py", 'if op == "stock":',
      'if op == "stock":\n            if not isinstance(key, str) or not key:\n                return {"error": "invalid"}')
    a(30, "Release wrongly requires reservation payload fields", "validation", "service.py", 'if op == "release":',
      'if op == "release":\n            if sku not in ("widget", "sensor") or type(qty) is not int:\n                return {"error": "invalid"}')
