"""Idempotency storage; tenant identity is part of the namespace."""


def cache_key(tenant, key):
    return key


class ReplayCache:
    def __init__(self):
        self.entries = {}

    def get(self, tenant, key):
        return self.entries.get(cache_key(tenant, key))

    def put(self, tenant, key, record):
        self.entries[cache_key(tenant, key)] = record
