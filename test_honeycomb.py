#!/usr/bin/env python3
"""
Test script to verify Honeycomb observability integration.

This script checks that:
1. All required OpenTelemetry packages are installed
2. The Honeycomb configuration module can be imported
3. Environment variables are set correctly (if applicable)
"""

import sys
import os

def check_imports():
    """Check that all required packages can be imported."""
    print("Checking OpenTelemetry package imports...")
    
    required_packages = [
        ("opentelemetry.trace", "opentelemetry-api"),
        ("opentelemetry.sdk.trace", "opentelemetry-sdk"),
        ("opentelemetry.exporter.otlp.proto.http.trace_exporter", "opentelemetry-exporter-otlp"),
        ("opentelemetry.instrumentation.fastapi", "opentelemetry-instrumentation-fastapi"),
        ("opentelemetry.processor.baggage", "opentelemetry-processor-baggage"),
    ]
    
    all_ok = True
    for module_name, package_name in required_packages:
        try:
            __import__(module_name)
            print(f"  ✓ {package_name}")
        except ImportError as e:
            print(f"  ✗ {package_name} - {e}")
            all_ok = False
    
    return all_ok

def check_honeycomb_module():
    """Check that the Honeycomb configuration module can be imported."""
    print("\nChecking Honeycomb module...")
    
    try:
        from backend.fastapi.observability.honeycomb import (
            configure_honeycomb,
            instrument_fastapi,
            get_tracer,
            add_span_attribute,
        )
        print("  ✓ Honeycomb module imported successfully")
        return True
    except ImportError as e:
        print(f"  ✗ Failed to import Honeycomb module: {e}")
        return False

def check_environment():
    """Check environment variable configuration."""
    print("\nChecking environment variables...")
    
    api_key = os.getenv("HONEYCOMB_API_KEY")
    service_name = os.getenv("OTEL_SERVICE_NAME", "tedxsdg-search-backend")
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "https://api.honeycomb.io:443")
    
    if api_key:
        # Mask the API key for security
        masked_key = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
        print(f"  ✓ HONEYCOMB_API_KEY: {masked_key}")
    else:
        print("  ⚠ HONEYCOMB_API_KEY: Not set (observability will be disabled)")
    
    print(f"  ✓ OTEL_SERVICE_NAME: {service_name}")
    print(f"  ✓ OTEL_EXPORTER_OTLP_ENDPOINT: {endpoint}")
    
    dataset = os.getenv("HONEYCOMB_DATASET")
    if dataset:
        print(f"  ✓ HONEYCOMB_DATASET: {dataset} (Honeycomb Classic)")
    
    return True

def test_configuration():
    """Test that Honeycomb can be configured."""
    print("\nTesting Honeycomb configuration...")
    
    try:
        from backend.fastapi.observability.honeycomb import configure_honeycomb
        
        # Try to configure (will return None if no API key)
        provider = configure_honeycomb(service_name="test-service")
        
        if provider:
            print("  ✓ Honeycomb configured successfully")
            print("  ✓ Tracer provider created")
            return True
        else:
            print("  ⚠ Honeycomb not configured (no API key)")
            print("  ℹ Set HONEYCOMB_API_KEY to enable observability")
            return True  # Not an error, just disabled
    except Exception as e:
        print(f"  ✗ Configuration failed: {e}")
        return False

def main():
    """Run all checks."""
    print("=" * 60)
    print("Honeycomb Observability Integration Test")
    print("=" * 60)
    
    results = []
    
    # Run checks
    results.append(("Package imports", check_imports()))
    results.append(("Honeycomb module", check_honeycomb_module()))
    results.append(("Environment variables", check_environment()))
    results.append(("Configuration test", test_configuration()))
    
    # Print summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("\n✓ All checks passed!")
        print("\nNext steps:")
        print("1. Set HONEYCOMB_API_KEY in your .env file")
        print("2. Run the application: ./run_fastapi-search.sh")
        print("3. Make some API requests")
        print("4. View traces in Honeycomb: https://ui.honeycomb.io/")
        return 0
    else:
        print("\n✗ Some checks failed. Please fix the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
