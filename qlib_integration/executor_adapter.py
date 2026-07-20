from __future__ import annotations

try:
    from qlib.backtest.executor import SimulatorExecutor
except ImportError:  # pragma: no cover
    SimulatorExecutor = object  # type: ignore[assignment,misc]


class AuditedSimulatorExecutor(SimulatorExecutor):  # type: ignore[misc]
    """SimulatorExecutor retaining the exchange's normalized audit event stream."""

    @property
    def execution_events(self) -> list[dict[str, object]]:
        return list(getattr(self.trade_exchange, "audit_events", []))
