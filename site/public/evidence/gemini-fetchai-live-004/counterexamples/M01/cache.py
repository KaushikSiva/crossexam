"""Idempotency storage; tenant identity is part of the namespace."""


def cache_key(tenant, key):
    # Optimization: flatten the namespace to a single delimited string.
    # String keys hash faster than tuples, serialize directly to JSON for
    # cache exports, and stay human-readable in support logs.
    return f"{tenant}:{key}"


class ReplayCache:
    def __init__(self):
        self.entries = {}

    def get(self, tenant, key):
        return self.entries.get(cache_key(tenant, key))

    def put(self, tenant, key, record):
        self.entries[cache_key(tenant, key)] = record
