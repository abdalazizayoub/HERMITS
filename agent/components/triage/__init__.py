from components.triage.prewarm_cache import PrewarmCache

__all__ = ["PrewarmCache", "TriagePoller", "ERPClient"]


def __getattr__(name: str):
    if name == "TriagePoller":
        from components.triage.poller import TriagePoller

        return TriagePoller
    if name == "ERPClient":
        from components.triage.poller import ERPClient

        return ERPClient
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
