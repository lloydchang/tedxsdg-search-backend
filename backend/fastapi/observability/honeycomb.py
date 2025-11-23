# File: backend/fastapi/observability/honeycomb.py

"""
Honeycomb observability configuration using OpenTelemetry.

This module configures OpenTelemetry to send traces, logs, and metrics to Honeycomb.
It follows the official Honeycomb documentation for Python OpenTelemetry SDK integration.
"""

import os
import logging
from typing import Optional

from opentelemetry import trace, baggage
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.processor.baggage import BaggageSpanProcessor, ALLOW_ALL_BAGGAGE_KEYS

logger = logging.getLogger(__name__)


def configure_honeycomb(
    service_name: str = "tedxsdg-search-backend",
    api_key: Optional[str] = None,
    dataset: Optional[str] = None,
    endpoint: Optional[str] = None,
    sample_rate: int = 1,
) -> Optional[TracerProvider]:
    """
    Configure OpenTelemetry to send telemetry data to Honeycomb.
    
    Args:
        service_name: Name of the service (used as dataset name in Honeycomb)
        api_key: Honeycomb API key (defaults to HONEYCOMB_API_KEY env var)
        dataset: Honeycomb dataset name (for Classic users, defaults to HONEYCOMB_DATASET env var)
        endpoint: Honeycomb endpoint (defaults to OTEL_EXPORTER_OTLP_ENDPOINT env var or US instance)
        sample_rate: Sample rate for traces (1 = no sampling, 2 = 50%, etc.)
    
    Returns:
        TracerProvider instance if configured successfully, None otherwise
    """
    # Get configuration from environment variables if not provided
    api_key = api_key or os.getenv("HONEYCOMB_API_KEY") or os.getenv("OTEL_EXPORTER_OTLP_HEADERS", "").split("x-honeycomb-team=")[-1].split(",")[0]
    endpoint = endpoint or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "https://api.honeycomb.io:443")
    dataset = dataset or os.getenv("HONEYCOMB_DATASET")
    
    # Check if Honeycomb is enabled
    if not api_key:
        logger.info("Honeycomb observability is disabled (no API key found)")
        return None
    
    logger.info(f"Configuring Honeycomb observability for service: {service_name}")
    
    # Create resource with service name and sample rate
    resource_attributes = {
        SERVICE_NAME: service_name,
    }
    
    # Add sample rate if specified
    if sample_rate > 1:
        resource_attributes["SampleRate"] = sample_rate
    
    resource = Resource.create(resource_attributes)
    
    # Create tracer provider
    tracer_provider = TracerProvider(resource=resource)
    
    # Configure OTLP exporter headers
    headers = {
        "x-honeycomb-team": api_key,
    }
    
    # Add dataset header for Honeycomb Classic users
    if dataset:
        headers["x-honeycomb-dataset"] = dataset
        logger.info(f"Using Honeycomb Classic dataset: {dataset}")
    
    # Create OTLP exporter
    otlp_exporter = OTLPSpanExporter(
        endpoint=f"{endpoint}/v1/traces",
        headers=headers,
    )
    
    # Add span processor with batching
    span_processor = BatchSpanProcessor(otlp_exporter)
    tracer_provider.add_span_processor(span_processor)
    
    # Add baggage processor to propagate baggage as span attributes
    baggage_processor = BaggageSpanProcessor(ALLOW_ALL_BAGGAGE_KEYS)
    tracer_provider.add_span_processor(baggage_processor)
    
    # Set the tracer provider as the global default
    trace.set_tracer_provider(tracer_provider)
    
    logger.info(f"Honeycomb observability configured successfully (endpoint: {endpoint})")
    
    return tracer_provider


def instrument_fastapi(app):
    """
    Instrument a FastAPI application with OpenTelemetry.
    
    Args:
        app: FastAPI application instance
    """
    try:
        FastAPIInstrumentor.instrument_app(app)
        logger.info("FastAPI instrumentation enabled")
    except Exception as e:
        logger.error(f"Failed to instrument FastAPI: {e}")


def get_tracer(name: str = __name__):
    """
    Get a tracer instance for creating custom spans.
    
    Args:
        name: Name of the tracer (typically the module name)
    
    Returns:
        Tracer instance
    """
    return trace.get_tracer(name)


def add_span_attribute(key: str, value):
    """
    Add an attribute to the current span.
    
    Args:
        key: Attribute key
        value: Attribute value
    """
    span = trace.get_current_span()
    if span:
        span.set_attribute(key, value)


def add_baggage_attribute(key: str, value: str):
    """
    Add a baggage attribute that will be propagated to all child spans.
    
    Note: Baggage attributes are attached to outgoing network requests as headers.
    Do NOT put sensitive information in baggage attributes.
    
    Args:
        key: Baggage key
        value: Baggage value (must be a string)
    
    Returns:
        Context token that should be detached when no longer needed
    """
    from opentelemetry.context import attach
    return attach(baggage.set_baggage(key, value))


def detach_baggage(token):
    """
    Detach a baggage context token.
    
    Args:
        token: Context token returned by add_baggage_attribute
    """
    from opentelemetry.context import detach
    detach(token)
