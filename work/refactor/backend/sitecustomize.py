"""Test runner environment tweaks.

Coverage's C tracer disagrees with certain C extensions (notably
dependency_injector.providers) and raises internal errors when pytest-cov
collects data across the suite. Setting COVERAGE_DISABLE_PYTRACER forces
coverage to fall back to the pure Python tracer, which stabilizes the run.
"""

import os

# Use the pure Python tracer to avoid `trace-changed` warnings and
# PyTracer stack underflows when dependency_injector manipulates tracing.
os.environ.setdefault("COVERAGE_DISABLE_PYTRACER", "1")
