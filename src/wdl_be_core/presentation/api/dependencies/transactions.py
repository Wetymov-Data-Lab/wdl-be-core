from fastapi import Request

from common.transaction_manager import AuditEntry

WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def request_audit_entry(request: Request) -> AuditEntry | None:
    """Build a server-controlled audit envelope after endpoint execution."""
    if request.method not in WRITE_METHODS:
        return None
    route = request.scope.get("route")
    action = getattr(route, "name", None) or f"http.{request.method.lower()}"
    path_params = {key: str(value) for key, value in request.path_params.items()}
    return AuditEntry(
        action=action,
        resource_type=next((part for part in request.url.path.split("/") if part), "root"),
        resource_id=getattr(request.state, "audit_resource_id", None)
        or next(
            (
                value
                for key, value in reversed(path_params.items())
                if key == "id" or key.endswith("_id")
            ),
            None,
        ),
        actor_id=getattr(request.state, "audit_actor_id", None),
        input={"path_params": path_params} if path_params else None,
        context={
            "method": request.method,
            "path": request.url.path,
            "request_id": request.headers.get("x-request-id"),
            "client_ip": request.client.host if request.client is not None else None,
        },
        trace_id=request.headers.get("traceparent") or request.headers.get("x-trace-id"),
    )
