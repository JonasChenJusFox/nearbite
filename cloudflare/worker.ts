import { DurableObject } from "cloudflare:workers";

interface Env {
  NEARBITE: DurableObjectNamespace<NearBiteContainer>;
  MONGO_URI?: string;
  MONGO_DBNAME: string;
  MONGO_TIMEOUT_MS: string;
  NEARBITE_SEARCH_MODE: string;
  STREAMLIT_SERVER_COOKIE_SECRET?: string;
}

const PORT = 8501;
const IDLE_TIMEOUT_MS = 10 * 60 * 1000;

export class NearBiteContainer extends DurableObject<Env> {
  private starting?: Promise<void>;

  constructor(ctx: DurableObjectState, env: Env) {
    super(ctx, env);
    if (ctx.container?.running) {
      ctx.blockConcurrencyWhile(() =>
        ctx.container!.setInactivityTimeout(IDLE_TIMEOUT_MS),
      );
    }
  }

  private async startAndWait(): Promise<void> {
    const container = this.ctx.container!;
    if (!container.running) {
      container.start({
        enableInternet: true,
        env: {
          PORT: String(PORT),
          MONGO_URI: this.env.MONGO_URI!,
          MONGO_DBNAME: this.env.MONGO_DBNAME,
          MONGO_TIMEOUT_MS: this.env.MONGO_TIMEOUT_MS,
          NEARBITE_SEARCH_MODE: this.env.NEARBITE_SEARCH_MODE,
          NEARBITE_REQUIRE_MONGO: "true",
          STREAMLIT_SERVER_COOKIE_SECRET: this.env.STREAMLIT_SERVER_COOKIE_SECRET!,
        },
      });
    }
    await container.setInactivityTimeout(IDLE_TIMEOUT_MS);

    const port = container.getTcpPort(PORT);
    const deadline = Date.now() + 60_000;
    while (Date.now() < deadline) {
      try {
        const response = await port.fetch("http://container/_stcore/health", {
          signal: AbortSignal.timeout(1000),
        });
        await response.body?.cancel();
        if (response.ok) return;
      } catch {
        // The VM may be running while Streamlit is still starting.
      }
      await scheduler.wait(500);
    }
    throw new Error("NearBite did not become healthy within 60 seconds");
  }

  async fetch(request: Request): Promise<Response> {
    this.starting ??= this.startAndWait().finally(() => {
      this.starting = undefined;
    });
    await this.starting;

    // The private container connection uses HTTP. Preserve the public host and
    // Origin so Streamlit's XSRF/WebSocket checks continue to work behind TLS.
    const url = new URL(request.url);
    const protocol = url.protocol.slice(0, -1);
    url.protocol = "http:";
    const forwarded = new Request(url, request);
    forwarded.headers.set("Host", url.host);
    forwarded.headers.set("X-Forwarded-Host", url.host);
    forwarded.headers.set("X-Forwarded-Proto", protocol);
    // Return upgrades directly; rebuilding the Response loses its WebSocket.
    return this.ctx.container!.getTcpPort(PORT).fetch(forwarded);
  }
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    if (!env.MONGO_URI?.trim() || !env.STREAMLIT_SERVER_COOKIE_SECRET?.trim()) {
      return new Response("NearBite deployment secrets are not configured.", {
        status: 503,
        headers: { "Cache-Control": "no-store" },
      });
    }

    // Streamlit stores sessions and generated media in process memory. Route
    // HTTP, assets, media, and WebSockets to the same container instance.
    try {
      return await env.NEARBITE.getByName("nearbite").fetch(request);
    } catch {
      console.error("NearBite container is unavailable");
      return new Response("NearBite is starting. Please retry shortly.", {
        status: 503,
        headers: { "Cache-Control": "no-store", "Retry-After": "10" },
      });
    }
  },
} satisfies ExportedHandler<Env>;
