"""Learning service: FSRS scheduling, recommendation, gamification (M4, M12, M13).

Runs in-process rather than as a separate deployment (ADR-0004). Must not import
from app.routers - enforced by an import-linter rule in CI.
"""
