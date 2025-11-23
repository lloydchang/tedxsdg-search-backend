# Honeycomb Observability Integration

This document explains how to use Honeycomb observability in the TEDxSDG Search Backend.

## Overview

The application is instrumented with [OpenTelemetry](https://opentelemetry.io/) to send traces to [Honeycomb](https://www.honeycomb.io/), providing deep visibility into:

- **Request performance**: Track search request latency and identify bottlenecks
- **Query patterns**: Understand what users are searching for (SDG queries vs general queries)
- **Search effectiveness**: Monitor result counts and filtering effectiveness
- **Error tracking**: Capture and analyze errors with full context

## Quick Start

### 1. Get Your Honeycomb API Key

1. Sign up for a free Honeycomb account at https://ui.honeycomb.io/signup
2. Navigate to **Account Settings** → **API Keys**
3. Create a new API key with "Can create datasets" permission
4. Copy the API key (you won't be able to see it again!)

### 2. Configure Environment Variables

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` and set your Honeycomb API key:

```bash
HONEYCOMB_API_KEY=your_actual_api_key_here
```

### 3. Install Dependencies

The required OpenTelemetry packages are already in `requirements.txt`. Install them:

```bash
pip install -r requirements.txt
```

### 4. Run the Application

Start the application normally:

```bash
./run_fastapi-search.sh
```

The application will automatically:
- Initialize OpenTelemetry
- Instrument FastAPI endpoints
- Send traces to Honeycomb

### 5. View Your Data in Honeycomb

1. Go to https://ui.honeycomb.io/
2. Select the `tedxsdg-search-backend` dataset
3. Start exploring your traces!

## Configuration Options

### Service Name

Set the service name (used as the dataset name in Honeycomb):

```bash
OTEL_SERVICE_NAME=tedxsdg-search-backend
```

### Honeycomb Endpoint

For EU users, change the endpoint:

```bash
OTEL_EXPORTER_OTLP_ENDPOINT=https://api.eu1.honeycomb.io:443
```

### Honeycomb Classic

If you're using Honeycomb Classic (not the current version), you need to specify a dataset:

```bash
HONEYCOMB_DATASET=your-dataset-name
```

### Sampling

To reduce data volume, you can sample traces. For example, to keep 50% of traces:

```bash
OTEL_TRACES_SAMPLER=traceidratio
OTEL_TRACES_SAMPLER_ARG=0.5
OTEL_RESOURCE_ATTRIBUTES=SampleRate=2
```

The `SampleRate` value should be `1/SAMPLER_ARG` (e.g., 0.5 sampling = SampleRate of 2).

## What Gets Tracked

### Automatic Instrumentation

FastAPI is automatically instrumented, tracking:
- HTTP request/response details
- Request duration
- Status codes
- Routes

### Custom Instrumentation

The `/api/search` endpoint includes custom spans and attributes:

#### Span Attributes

- `query`: The original search query
- `request_id`: Unique request identifier
- `client_ip`: Client IP address
- `query.normalized`: Normalized query string
- `query.is_sdg`: Whether this is an SDG-specific query
- `query.sdg_number`: SDG number (if applicable)
- `search.type`: Type of search (`sdg_tag` or `general`)
- `search.sdg_tag`: SDG tag being searched (if applicable)
- `query.augmented`: Augmented query with SDG keywords
- `sdg_results.count`: Number of SDG-filtered results
- `semantic_results.count`: Number of semantic search results
- `presenter_results.count`: Number of presenter-filtered results
- `results.final_count`: Final number of results returned
- `search.duration_seconds`: Total search duration
- `error`: Whether an error occurred
- `error.type`: Type of error (`cache_error` or `search_error`)
- `error.message`: Error message

#### Custom Spans

- `search_request`: Main search operation
- `filter_by_sdg_tag`: SDG tag filtering
- `semantic_search`: Semantic search operation
- `parallel_search`: Parallel presenter and semantic search

## Adding Custom Instrumentation

### Creating Custom Spans

To add custom spans to track specific operations:

```python
from backend.fastapi.observability.honeycomb import get_tracer

tracer = get_tracer(__name__)

with tracer.start_as_current_span("my_operation"):
    # Your code here
    result = do_something()
```

### Adding Span Attributes

To add attributes to the current span:

```python
from backend.fastapi.observability.honeycomb import add_span_attribute

add_span_attribute("user_id", user_id)
add_span_attribute("operation_type", "batch_processing")
add_span_attribute("items_processed", 42)
```

### Using Baggage for Multi-Span Attributes

To add an attribute that propagates to all child spans:

```python
from backend.fastapi.observability.honeycomb import add_baggage_attribute, detach_baggage

# Add baggage
token = add_baggage_attribute("user_id", str(user_id))

try:
    # All spans created here will have the user_id attribute
    with tracer.start_as_current_span("operation_1"):
        # ...
    
    with tracer.start_as_current_span("operation_2"):
        # ...
finally:
    # Always detach baggage when done
    detach_baggage(token)
```

**Warning**: Baggage attributes are sent as HTTP headers. Never put sensitive information in baggage!

## Querying Data in Honeycomb

### Example Queries

**Average search duration by query type:**
```
BREAKDOWN: search.type
CALCULATE: AVG(search.duration_seconds)
```

**Top 10 most common queries:**
```
BREAKDOWN: query
CALCULATE: COUNT
ORDER BY: COUNT DESC
LIMIT: 10
```

**Error rate:**
```
BREAKDOWN: error.type
CALCULATE: COUNT
WHERE: error = true
```

**SDG query distribution:**
```
BREAKDOWN: query.sdg_number
CALCULATE: COUNT
WHERE: query.is_sdg = true
```

**P95 latency for semantic search:**
```
CALCULATE: P95(duration_ms)
WHERE: name = "semantic_search"
```

## Troubleshooting

### No Data Appearing in Honeycomb

1. **Check your API key**: Make sure `HONEYCOMB_API_KEY` is set correctly
2. **Check the logs**: Look for "Honeycomb observability configured successfully" in the startup logs
3. **Verify network connectivity**: Ensure your application can reach `api.honeycomb.io`
4. **Check for errors**: Look for OpenTelemetry-related errors in the logs

### Seeing "Honeycomb observability is disabled"

This means no API key was found. Set the `HONEYCOMB_API_KEY` environment variable.

### High Data Volume

If you're sending too much data:

1. **Enable sampling**: Set `OTEL_TRACES_SAMPLER=traceidratio` and `OTEL_TRACES_SAMPLER_ARG=0.1` (for 10% sampling)
2. **Add the SampleRate attribute**: Set `OTEL_RESOURCE_ATTRIBUTES=SampleRate=10`
3. **Filter noisy endpoints**: Modify the instrumentation to exclude health checks or other high-frequency endpoints

## Disabling Honeycomb

To disable Honeycomb observability, simply remove or comment out the `HONEYCOMB_API_KEY` environment variable. The application will detect this and skip instrumentation.

## Learn More

- [Honeycomb Documentation](https://docs.honeycomb.io/)
- [OpenTelemetry Python Documentation](https://opentelemetry.io/docs/instrumentation/python/)
- [Honeycomb Best Practices](https://docs.honeycomb.io/working-with-your-data/best-practices/)
- [Honeycomb Query Language](https://docs.honeycomb.io/working-with-your-data/queries/)

## Support

For issues with:
- **This integration**: Open an issue in this repository
- **Honeycomb**: Visit https://www.honeycomb.io/support
- **OpenTelemetry**: Visit https://opentelemetry.io/community/
