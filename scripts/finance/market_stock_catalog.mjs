// Finance Market STOCKS M16: bounded EOD-only issuer universe.
// This is separate from the SEC filing-price allowlist on purpose.
// Only AAPL can use the existing no-key demo path; MSFT is an uncertain
// demo trial; all other issuers require the existing private EODHD token.
// An allowlisted symbol is NOT a guarantee of provider plan entitlement.
export const STOCK_SYMBOLS = Object.freeze({
  "0000320193": "AAPL.US",
  "0000789019": "MSFT.US",
  "0001045810": "NVDA.US",
  "0001018724": "AMZN.US",
  "0001318605": "TSLA.US",
  "0001652044": "GOOGL.US",
});
