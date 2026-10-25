// FinanceW M7 standalone, opt-in loopback read-only market-data server.
// Never auto-starts from Quickshell, shell startup or import.
// GET /v1/health and GET /v1/price-context?cik=##########&date=YYYY-MM-DD
import { createServer } from "node:http";
import { pathToFileURL } from "node:url";
import { createMarketDataHub } from "./market_data_hub.mjs";

const DEFAULT_PORT = 48731;
const MAX_REQUEST_PATH = 256;
const CLIENT_HEADER = "financew";
function reply(response, status, body) {
  response.writeHead(status, {
    "Content-Type": "application/json; charset=utf-8",
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff"
  });
  response.end(JSON.stringify(body) + "\n");
}
const ERRORS = new Set([
  "invalid-selection", "unknown-provider", "provider-busy",
  "provider-key-required", "demo-not-authorized", "provider-unavailable",
  "provider-response-too-large", "provider-invalid", "invalid-price-data",
  "invalid-provider-snapshot", "token-unreadable", "token-permissions",
  "token-invalid", "provider-failed"
]);

export function createMarketDataServer({hub=createMarketDataHub()}={}) {
  return createServer(async (request, response) => {
    // Both the bind address and the application header are intentionally
    // restricted. This is NOT authentication or an internet-facing API.
    const address = request.socket.localAddress;
    const port = request.socket.localPort;
    if (address !== "127.0.0.1" || request.headers.host !== "127.0.0.1:" + port
        || request.headers.origin || request.headers["x-post-apollo-client"] !== CLIENT_HEADER) {
      reply(response,403,{error:"local-client-only"}); return;
    }
    if (request.method !== "GET") {
      reply(response,405,{error:"read-only-method"}); return;
    }
    if (!request.url || request.url.length > MAX_REQUEST_PATH) {
      reply(response,400,{error:"invalid-selection"}); return;
    }
    let url;
    try { url = new URL(request.url, "http://127.0.0.1:" + port); }
    catch {reply(response,400,{error:"invalid-selection"});return;}
    if (url.pathname === "/v1/health" && url.search === "") {
      reply(response,200,hub.health()); return;
    }
    if (url.pathname !== "/v1/price-context"
        || Array.from(url.searchParams.keys()).some(k=>!["cik","date","provider"].includes(k))
        || ["cik","date","provider"].some(k=>url.searchParams.getAll(k).length>1)) {
      reply(response,404,{error:"unknown-route"}); return;
    }
    try {
      const payload = await hub.getPriceContext({
        cik:url.searchParams.get("cik"),
        filingDate:url.searchParams.get("date"),
        provider:url.searchParams.get("provider") || "eodhd"
      });
      reply(response,200,payload);
    } catch (error) {
      const code = ERRORS.has(error?.code) ? error.code : "provider-failed";
      const status = code === "invalid-selection" || code === "unknown-provider" ? 400
        : code === "provider-busy" ? 429 : 503;
      reply(response,status,{error:code});
    }
  });
}

// Direct invocation is an explicit opt-in; no auto-managed user service,
// no network bind to any non-loopback interface.
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const raw = process.env.POST_APOLLO_MARKET_HUB_PORT;
  const port = raw === undefined ? DEFAULT_PORT : Number(raw);
  if (!Number.isInteger(port) || port < 1024 || port > 65535) {
    process.stderr.write("POST_APOLLO_MARKET_HUB_ERROR invalid-port\n");
    process.exitCode=1;
  } else {
    const server=createMarketDataServer();
    server.on("error", () => {
      process.stderr.write("POST_APOLLO_MARKET_HUB_ERROR bind-failed\n");
      process.exitCode=1;
    });
    server.listen(port,"127.0.0.1", () => {
      process.stdout.write("POST_APOLLO_MARKET_HUB_READY 127.0.0.1:" + port + "\n");
    });
  }
}
