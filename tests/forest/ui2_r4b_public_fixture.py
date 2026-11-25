"""Recorded actual R4b producer callbacks; no UI callback or model execution."""
import json
from test_runtime_public_delivery_r4b import LocalDeliveryTests

fixture = LocalDeliveryTests()
fixture.setUp()
try:
    delivery = fixture.delivery()
    for frame in fixture.frames():
        delivery.observe(frame)
    delivery.withdraw()
    print(json.dumps(fixture.units, separators=(",", ":")))
finally:
    fixture.doCleanups()
