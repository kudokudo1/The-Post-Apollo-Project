# M46e2 explicit demo path
EODHD documentation reviewed 2026-11-25:
- https://eodhd.com/financial-apis/api-for-historical-data-and-volumes
- https://eodhd.com/help/plans
The lists differ (notably MSFT and AMZN). Initial scope is only the common documented equity symbols AAPL.US and TSLA.US. Not live entitlement evidence. No other symbols, ETFs, forex or crypto are enabled.
Select a US OpenFIGI result for AAPL or TSLA, choose the explicit documented demo listing in the same inline EODHD controls, set dates, and manually load. Fixed catalog metadata is not a provider search response; currencySource is eodhd-demo-catalog, identityVerified remains false. The existing 20/day local reservation cap applies conservatively, even for demo. No automatic fallback, private token access or subscription changes. Demo and keyed references cannot mix in comparative analysis.
No live provider or desktop acceptance in this PR. Stacked on #2734; review/merge/activation separately.