"""LLM providers, caching, budgeting and routing.

Everything above this package calls `ProviderRouter.generate` and never knows
which provider answered — including when the answer came from authored content
because no provider was available.
"""
