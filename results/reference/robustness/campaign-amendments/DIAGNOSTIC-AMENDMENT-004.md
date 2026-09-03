# Diagnostic Amendment 004 — safety HTTP error body capture

The safety publisher previously retained only the HTTP status and discarded the controller response body. This instrumentation-only amendment records the failing observation sequence and response body. It changes no request, retry behavior, timing, workload, controller, or acceptance rule. Any diagnostic attempt that fails remains invalid and excluded.
