# Honeycomb Quick Reference

## Setup (One-Time)

```bash
# 1. Copy environment template
cp .env.example .env

# 2. Edit .env and add your API key
# HONEYCOMB_API_KEY=your_api_key_here

# 3. Install dependencies
pip install -r requirements.txt

# 4. Test the integration
python test_honeycomb.py

# 5. Run the application
./run_fastapi-search.sh
```

## Common Code Patterns

### Creating a Custom Span

```python
from backend.fastapi.observability.honeycomb import get_tracer

tracer = get_tracer(__name__)

with tracer.start_as_current_span("operation_name"):
    # Your code here
    result = do_something()
```

### Adding Span Attributes

```python
from backend.fastapi.observability.honeycomb import add_span_attribute

add_span_attribute("user_id", user_id)
add_span_attribute("items_count", len(items))
add_span_attribute("operation_type", "batch")
```

### Nested Spans

```python
with tracer.start_as_current_span("parent_operation"):
    add_span_attribute("parent_attr", "value")
    
    with tracer.start_as_current_span("child_operation"):
        add_span_attribute("child_attr", "value")
        # Child span inherits parent context
```

### Tracking Errors

```python
with tracer.start_as_current_span("risky_operation") as span:
    try:
        result = might_fail()
    except Exception as e:
        add_span_attribute("error", True)
        add_span_attribute("error.type", type(e).__name__)
        add_span_attribute("error.message", str(e))
        raise
```

### Using Baggage (Advanced)

```python
from backend.fastapi.observability.honeycomb import (
    add_baggage_attribute,
    detach_baggage
)

# Add baggage that propagates to all child spans
token = add_baggage_attribute("request_id", str(request_id))

try:
    with tracer.start_as_current_span("operation_1"):
        pass  # Will have request_id attribute
    
    with tracer.start_as_current_span("operation_2"):
        pass  # Will also have request_id attribute
finally:
    # Always detach!
    detach_baggage(token)
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `HONEYCOMB_API_KEY` | Yes* | - | Your Honeycomb API key |
| `OTEL_SERVICE_NAME` | No | `tedxsdg-search-backend` | Service/dataset name |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | No | `https://api.honeycomb.io:443` | Honeycomb endpoint |
| `HONEYCOMB_DATASET` | No** | - | Dataset (Classic only) |

\* Required to enable observability  
\** Only for Honeycomb Classic users

## Honeycomb UI Quick Actions

### View Recent Traces
1. Go to https://ui.honeycomb.io/
2. Select `tedxsdg-search-backend` dataset
3. Click "Recent Traces"

### Query by Attribute
```
WHERE query.is_sdg = true
```

### Calculate Average Duration
```
CALCULATE: AVG(search.duration_seconds)
```

### Group by Query Type
```
BREAKDOWN: search.type
CALCULATE: COUNT
```

### Find Errors
```
WHERE error = true
ORDER BY: timestamp DESC
```

### P95 Latency
```
CALCULATE: P95(duration_ms)
WHERE: name = "search_request"
```

## Useful Span Attributes

### Request Context
- `query` - Original search query
- `request_id` - Unique request ID
- `client_ip` - Client IP address

### Query Analysis
- `query.normalized` - Normalized query
- `query.is_sdg` - Is SDG query?
- `query.sdg_number` - SDG number (if applicable)
- `query.augmented` - Augmented query with keywords

### Search Metadata
- `search.type` - Search type (sdg_tag/general)
- `search.sdg_tag` - SDG tag being searched

### Results
- `results.final_count` - Final result count
- `results.slugs` - List of returned slugs
- `results.score.max` - Max relevance score
- `results.score.avg` - Average relevance score
- `results.empty` - True if no results

### Semantic Search Internals
- `calculation.duration_seconds` - Core calculation time
- `tfidf.document_count` - Total documents scanned
- `query.token_count` - Query complexity

### Performance
- `search.duration_seconds` - Total search duration
- `http.duration_seconds` - Global request duration

### Errors
- `error` - Boolean, true if error occurred
- `error.type` - Error type/class name
- `error.message` - Error message

## Common Queries

### Top 10 Queries
```
BREAKDOWN: query
CALCULATE: COUNT
ORDER BY: COUNT DESC
LIMIT: 10
```

### SDG Distribution
```
BREAKDOWN: query.sdg_number
CALCULATE: COUNT
WHERE: query.is_sdg = true
```

### Average Results per Query Type
```
BREAKDOWN: search.type
CALCULATE: AVG(results.final_count)
```

### Slowest Queries
```
BREAKDOWN: query
CALCULATE: P95(search.duration_seconds)
ORDER BY: P95(search.duration_seconds) DESC
LIMIT: 10
```

### Error Rate by Type
```
BREAKDOWN: error.type
CALCULATE: COUNT
WHERE: error = true
```

### Requests Over Time
```
VISUALIZE: COUNT
GROUP BY: time (1 minute)
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| No data in Honeycomb | Check `HONEYCOMB_API_KEY` is set |
| "Observability disabled" message | Set `HONEYCOMB_API_KEY` in `.env` |
| Import errors | Run `pip install -r requirements.txt` |
| High data volume | Enable sampling (see HONEYCOMB.md) |
| Missing attributes | Check span is active when adding attributes |

## Testing

```bash
# Run integration test
python test_honeycomb.py

# Make a test request
curl "http://localhost:8000/api/search?query=sdg7"

# Check Honeycomb UI for the trace
```

## Sampling Configuration

```bash
# Sample 50% of traces
OTEL_TRACES_SAMPLER=traceidratio
OTEL_TRACES_SAMPLER_ARG=0.5
OTEL_RESOURCE_ATTRIBUTES=SampleRate=2

# Sample 10% of traces
OTEL_TRACES_SAMPLER=traceidratio
OTEL_TRACES_SAMPLER_ARG=0.1
OTEL_RESOURCE_ATTRIBUTES=SampleRate=10
```

## Links

- **Setup Guide**: [HONEYCOMB.md](HONEYCOMB.md)
- **Architecture**: [HONEYCOMB_ARCHITECTURE.md](HONEYCOMB_ARCHITECTURE.md)
- **Summary**: [HONEYCOMB_SUMMARY.md](HONEYCOMB_SUMMARY.md)
- **Honeycomb Docs**: https://docs.honeycomb.io/
- **OpenTelemetry Docs**: https://opentelemetry.io/docs/instrumentation/python/

## Best Practices

✅ **DO:**
- Use descriptive span names
- Add relevant attributes
- Track errors with context
- Sample in production
- Detach baggage tokens

❌ **DON'T:**
- Log sensitive data (passwords, API keys, PII)
- Create too many spans (overhead)
- Forget to detach baggage
- Put sensitive data in baggage (sent as headers)
- Block on span creation

## Support

- **Integration Issues**: Open an issue in this repo
- **Honeycomb Support**: https://www.honeycomb.io/support
- **OpenTelemetry**: https://opentelemetry.io/community/
