# File: backend/fastapi/observability/middleware.py

import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.types import ASGIApp
from backend.fastapi.observability.honeycomb import add_span_attribute, get_tracer

class ObservabilityMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add global observability attributes to every request.
    """
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.tracer = get_tracer(__name__)

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Add request attributes
        # Note: Some of these might be handled by auto-instrumentation, 
        # but adding them explicitly ensures they are available in the root span context
        # if we want to access them easily in custom spans.
        
        # We can't easily access the current span here because the middleware 
        # runs before the route handler where the auto-instrumentation span is fully active/accessible 
        # in the same way. However, we can try to get the current span.
        
        response = await call_next(request)
        
        duration = time.time() - start_time
        
        # We can add attributes to the current span (which should be the server span)
        # after the request is processed
        try:
            add_span_attribute("http.response_size", response.headers.get("content-length", 0))
            add_span_attribute("http.duration_seconds", duration)
            add_span_attribute("api.endpoint", request.url.path)
            
            # Add custom header to response for debugging/tracing
            # response.headers["X-Trace-Duration"] = str(duration)
            
        except Exception:
            # Don't fail the request if observability fails
            pass
            
        return response
