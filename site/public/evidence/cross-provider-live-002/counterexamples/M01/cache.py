"""Idempotency storage; tenant identity is part of the namespace."""


def cache_key(tenant, key):
    # Subtly faulty: normalize tenant to lowercase for lookup/storage keys.
    # This violates the contract which states tenants are nonempty strings and
    # idempotency is scoped to the exact (tenant, key) tuple with no case folding.
    return (tenant.lower(), key)


class ReplayCache:
    def __init__(self):
        self.entries = {}

    def get(self, tenant, key):
        return self.entries.get(cache_key(tenant, key))

    def put(self, tenant, key, record):
        self.entries[cache_key(tenant, key)] = record
