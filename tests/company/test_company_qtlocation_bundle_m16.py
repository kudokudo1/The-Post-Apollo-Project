"""Compatibility entry point for M16 CI after the M17 full-QML bundle upgrade.

M16's original library-only fixtures are no longer valid: a QtLocation QML
import requires the library AND the QML module files. Run the stricter M17
bundle integrity, rollback, host linkage, and missing-plugin tests here.
"""
from test_company_qtlocation_qml_m17 import BundleTests, BridgeTests
