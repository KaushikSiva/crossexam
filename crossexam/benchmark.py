"""Fixed, inspectable defect corpus. Split membership is never sent to models.

Validation guides promotion. Audit is opened only after promotion finishes.
These are synthetic, hand-designed defects, not representative industry rates.
"""

from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "fixtures" / "relayqueue"


@dataclass
class Variant:
    id: str
    title: str
    family: str
    split: str
    files: dict
    correct: bool = False
    origin: str = "hand-authored benchmark"


def source():
    return {name: (FIXTURE / name).read_text() for name in ("service.py", "cache.py")}


def corpus():
    base = source()
    variants = []

    def add(id, title, family, split, filename, before, after, correct=False):
        files = dict(base)
        if files[filename].count(before) != 1:
            raise ValueError(f"Mutation anchor for {id} is not unique")
        files[filename] = files[filename].replace(before, after)
        variants.append(Variant(id, title, family, split, files, correct))

    add("D01", "Global replay cache leaks reservations", "tenant_isolation", "discovery", "cache.py",
        "return (tenant, key)", "return key")
    add("D02", "Retries consume inventory twice", "idempotency", "discovery", "service.py",
        'return record["response"].copy()',
        'self.stock[(tenant, sku)] = self.stock.get((tenant, sku), 10) - qty\n            return record["response"].copy()')
    add("D03", "Changed payload silently reuses a key", "payload_binding", "discovery", "service.py",
        'if record["sku"] != sku or record["qty"] != qty:', 'if False:')
    add("D04", "Repeated release creates inventory", "inventory", "discovery", "service.py",
        'if not record["released"]:', 'if True:')
    add("D05", "Negative reservations increase stock", "validation", "discovery", "service.py",
        'not 1 <= qty <= 10', 'not -10 <= qty <= 10')

    add("V01", "Case-folded tenant namespaces collide", "tenant_isolation", "validation", "cache.py",
        "return (tenant, key)", "return (tenant.lower(), key)")
    add("V02", "Delimited tuple keys are ambiguous", "tenant_isolation", "validation", "cache.py",
        "return (tenant, key)", 'return tenant + ":" + key')
    add("V03", "Released reservations can be replayed as new", "idempotency", "validation", "service.py",
        'record["released"] = True', 'record["released"] = True\n                self.cache.entries.pop((tenant, key), None)')
    add("V04", "Product changes under an existing key", "payload_binding", "validation", "service.py",
        'if record["sku"] != sku or record["qty"] != qty:', 'if record["qty"] != qty:')
    add("V05", "Last available unit cannot be reserved", "inventory", "validation", "service.py",
        "if available < qty:", "if available <= qty:")
    add("V06", "Booleans accepted as quantities", "validation", "validation", "service.py",
        "type(qty) is not int", "not isinstance(qty, int)")
    add("V07", "Tenants share the same inventory bucket", "inventory", "validation", "service.py",
        "slot = (tenant, sku)", 'slot = ("shared", sku)')
    add("V08", "Zero quantity accepted", "validation", "validation", "service.py",
        "not 1 <= qty <= 10", "not 0 <= qty <= 10")

    add("A01", "Tenant prefix optimization aliases organizations", "tenant_isolation", "audit", "cache.py",
        "return (tenant, key)", 'return (tenant.split("-")[0], key)')
    add("A02", "Replay availability check precedes idempotency", "idempotency", "audit", "service.py",
        'if record is not None:\n            if',
        'if record is not None:\n            if self.stock.get((tenant, sku), 10) < qty:\n                return {"error": "insufficient"}\n            if')
    add("A03", "Quantity changes slip through payload binding", "payload_binding", "audit", "service.py",
        'if record["sku"] != sku or record["qty"] != qty:', 'if record["sku"] != sku:')
    add("A04", "Release restores only one unit", "inventory", "audit", "service.py",
        'self.stock.get(slot, 10) + record["qty"]', 'self.stock.get(slot, 10) + 1')
    add("A05", "Integral floats pass quantity validation", "validation", "audit", "service.py",
        "type(qty) is not int", "type(qty) not in (int, float)")
    add("A06", "Retry of released key consumes stock again", "idempotency", "audit", "service.py",
        'return record["response"].copy()',
        'if record["released"]:\n                self.stock[(tenant, sku)] = self.stock.get((tenant, sku), 10) - qty\n            return record["response"].copy()')
    add("A07", "Empty tenants accepted", "validation", "audit", "service.py",
        'not isinstance(tenant, str) or not tenant', 'not isinstance(tenant, str)')
    add("A08", "Foreign release finds another tenant's key", "tenant_isolation", "audit", "service.py",
        'if op == "release":\n            record = self.cache.get(tenant, key)',
        'if op == "release":\n            record = self.cache.get(tenant, key)\n            if record is None:\n                record = next((v for k, v in self.cache.entries.items() if k[1] == key), None)')

    variants.append(Variant("C01", "Reference implementation", "control", "control", dict(base), True))
    add("C02", "Equivalent response copy refactor", "control", "control", "service.py",
        'return record["response"].copy()', 'return dict(record["response"])', True)
    add("C03", "Equivalent boundary expression", "control", "control", "service.py",
        "if available < qty:", "if qty > available:", True)
    add("C04", "Equivalent tuple construction", "control", "control", "cache.py",
        "return (tenant, key)", "return tuple([tenant, key])", True)
    return variants
