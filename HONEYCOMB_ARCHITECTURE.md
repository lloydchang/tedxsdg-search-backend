# Honeycomb Observability Architecture

## Data Flow Diagram

```mermaid
graph TB
    subgraph "Client"
        A[User Request]
    end
    
    subgraph "FastAPI Application"
        B[FastAPI Endpoint]
        C[OpenTelemetry Instrumentation]
        D[Custom Spans]
        E[Search Logic]
    end
    
    subgraph "OpenTelemetry SDK"
        F[Tracer Provider]
        G[Span Processor]
        H[Baggage Processor]
        I[OTLP Exporter]
    end
    
    subgraph "Honeycomb"
        J[Honeycomb API]
        K[Trace Storage]
        L[Query Interface]
    end
    
    A -->|HTTP Request| B
    B -->|Auto-instrumentation| C
    C -->|Create Span| F
    B --> E
    E -->|Custom Spans| D
    D -->|Add Attributes| F
    F --> G
    F --> H
    G -->|Batch Spans| I
    H -->|Add Baggage| I
    I -->|OTLP/HTTP| J
    J --> K
    K --> L
    L -->|View Traces| M[Developer]
    
    style C fill:#f9f,stroke:#333,stroke-width:2px
    style D fill:#f9f,stroke:#333,stroke-width:2px
    style I fill:#9cf,stroke:#333,stroke-width:2px
    style J fill:#9f9,stroke:#333,stroke-width:2px
```

## Trace Structure

```mermaid
graph LR
    subgraph "HTTP Request Trace"
        A[GET /api/search]
        A --> B[search_request]
        B --> C{Query Type?}
        C -->|SDG| D[filter_by_sdg_tag]
        C -->|SDG| E[semantic_search]
        C -->|General| F[parallel_search]
        F --> G[presenter_search]
        F --> H[semantic_search]
    end
    
    style A fill:#e1f5ff,stroke:#333,stroke-width:2px
    style B fill:#fff4e1,stroke:#333,stroke-width:2px
    style D fill:#e8f5e9,stroke:#333,stroke-width:2px
    style E fill:#e8f5e9,stroke:#333,stroke-width:2px
    style F fill:#fff4e1,stroke:#333,stroke-width:2px
```

## Span Attributes

### Root Span (HTTP Request)
```
http.method: GET
http.route: /api/search
http.status_code: 200
http.url: /api/search?query=sdg7
```

### search_request Span
```
query: "sdg7"
request_id: "abc-123-def-456"
client_ip: "192.168.1.1"
query.normalized: "sdg7"
query.is_sdg: true
query.sdg_number: 7
search.type: "sdg_tag"
search.sdg_tag: "sdg7"
query.augmented: "sdg7 clean energy renewable..."
results.final_count: 10
search.duration_seconds: 0.1234
```

### filter_by_sdg_tag Span
```
sdg_results.count: 25
```

### semantic_search Span
```
semantic_results.count: 15
```

## Configuration Flow

```mermaid
sequenceDiagram
    participant App as FastAPI App
    participant HC as Honeycomb Module
    participant OT as OpenTelemetry SDK
    participant API as Honeycomb API
    
    App->>HC: configure_honeycomb()
    HC->>HC: Load env vars
    HC->>OT: Create TracerProvider
    HC->>OT: Create OTLP Exporter
    HC->>OT: Add Span Processor
    HC->>OT: Add Baggage Processor
    HC->>OT: Set Global Provider
    HC-->>App: TracerProvider
    
    App->>HC: instrument_fastapi(app)
    HC->>OT: FastAPIInstrumentor.instrument_app()
    
    Note over App,API: Application is now instrumented
    
    App->>App: Handle Request
    App->>OT: Create Span
    App->>OT: Add Attributes
    OT->>API: Send Trace (async)
    API-->>OT: ACK
```

## Environment Configuration

```mermaid
graph TD
    A[.env file] -->|Load| B{HONEYCOMB_API_KEY set?}
    B -->|Yes| C[Enable Observability]
    B -->|No| D[Disable Observability]
    
    C --> E[Configure Endpoint]
    E --> F{Honeycomb Classic?}
    F -->|Yes| G[Set Dataset Header]
    F -->|No| H[Use Service Name]
    
    G --> I[Initialize Tracer]
    H --> I
    I --> J[Instrument FastAPI]
    J --> K[Ready to Send Traces]
    
    D --> L[Skip Instrumentation]
    L --> M[Normal Operation]
    
    style C fill:#9f9,stroke:#333,stroke-width:2px
    style D fill:#f99,stroke:#333,stroke-width:2px
    style K fill:#9cf,stroke:#333,stroke-width:2px
```

## Key Components

### 1. Tracer Provider
- Central component managing trace creation
- Configured with service name and resource attributes
- Manages span processors

### 2. OTLP Exporter
- Exports traces to Honeycomb via HTTP
- Uses OTLP (OpenTelemetry Protocol)
- Includes Honeycomb API key in headers

### 3. Span Processor
- Batches spans for efficient export
- Handles async sending to reduce latency
- Configurable batch size and timeout

### 4. Baggage Processor
- Propagates baggage as span attributes
- Useful for cross-cutting concerns
- Automatically adds to all child spans

### 5. FastAPI Instrumentor
- Automatically instruments all endpoints
- Captures HTTP metadata
- Creates parent spans for requests

## Data Types Tracked

### Traces
- Request flow through the application
- Parent-child span relationships
- Timing information

### Spans
- Individual operations within a trace
- Start and end times
- Status (OK, ERROR)

### Attributes
- Key-value pairs attached to spans
- Query parameters
- Result counts
- Performance metrics
- Error information

### Events
- Point-in-time occurrences
- Errors and exceptions
- Log messages (if enabled)

## Best Practices

1. **Use Descriptive Span Names**: Name spans after the operation, not the function
2. **Add Relevant Attributes**: Include context that helps debugging
3. **Create Spans for Expensive Operations**: Track database queries, API calls, etc.
4. **Don't Over-Instrument**: Too many spans can add overhead
5. **Use Baggage Sparingly**: Only for truly cross-cutting data
6. **Never Log Sensitive Data**: No passwords, API keys, PII in attributes
7. **Sample in Production**: Use sampling to control data volume
8. **Monitor Exporter Health**: Check for export failures

## Performance Impact

- **Minimal Overhead**: ~1-2ms per request
- **Async Export**: Doesn't block request handling
- **Batching**: Reduces network calls
- **Sampling**: Can reduce overhead further

## Security Considerations

- API key stored in environment variable (not in code)
- `.env` file in `.gitignore`
- No sensitive data in span attributes
- HTTPS for all communication with Honeycomb
- Baggage not used for sensitive data (sent in headers)
