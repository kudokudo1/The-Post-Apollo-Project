// M46d1: staged range-only adapter. NOT selected by any production entrypoint.
// Both dependencies are mandatory: explicit ownership/activation is separate.
import {loadPriceRange} from "./read_market_price_range.mjs";
import {quotaFetcher} from "./market_shared_quota.mjs";

export function createRangeQuotaCandidate({upstream,reserver,tokenLoader,today}={}) {
  if (typeof upstream!=="function" || typeof reserver!=="function"
      || typeof tokenLoader!=="function" || typeof today!=="function")
    throw new Error("quota-candidate-dependencies-required");
  return async (cik,from,to)=>{
    // Instantiate per read; no shared mutable receipt across concurrent calls.
    // Validation and token eligibility happen in loadPriceRange BEFORE fetcher.
    const guarded=quotaFetcher("eodhd",upstream,reserver);
    return loadPriceRange(cik,from,to,guarded.fetcher,tokenLoader,today());
  };
}
