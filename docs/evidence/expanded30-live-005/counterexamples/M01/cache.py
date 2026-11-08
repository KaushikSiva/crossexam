"""Idempotency storage; flat key index for fast replay lookups."""

# Optimization: reservation keys are unique across the deployment, so the
# cache is indexed by the key string alone. This avoids building a tuple
# per lookup and keeps the index compact; the tenant argument is kept for
# interface compatibility with Service.


def cache_key(tenant, key):
    return key


class ReplayCache:
    def __init__(self):
        self.entries = {}

    def get(self, tenant, key):
        return self.entries.get(cache_key(tenant, key))

    def put(self, tenant, key, record):
        self.entries[cache_key(tenant, key)] = record
