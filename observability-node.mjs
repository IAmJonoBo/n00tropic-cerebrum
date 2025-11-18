import process from "node:process";

const BOOL_TRUE = new Set(["1", "true", "yes", "on"]);
const DEFAULT_GRPC_ENDPOINT = "grpc://127.0.0.1:4317";

const noopTracing = {
  tracer: null,
  isEnabled: false,
  withSpan: async (_name, fn) => fn(undefined),
};

let cachedTracing;

function asBool(value) {
  if (typeof value !== "string") {
    return false;
  }
  return BOOL_TRUE.has(value.trim().toLowerCase());
}

function normalizeGrpcEndpoint(value) {
  const raw = (value || DEFAULT_GRPC_ENDPOINT).trim();
  if (!raw) {
    return DEFAULT_GRPC_ENDPOINT;
  }
  if (raw.startsWith("grpc://") || raw.startsWith("grpcs://")) {
    return raw;
  }
  if (raw.startsWith("http://")) {
    return `grpc://${raw.slice(7)}`;
  }
  if (raw.startsWith("https://")) {
    return `grpcs://${raw.slice(8)}`;
  }
  return raw.includes("://") ? raw : `grpc://${raw}`;
}

function createSpanRunner(api, tracer) {
  const { context, trace, SpanStatusCode } = api;
  return async function withSpan(name, fn) {
    if (!tracer) {
      return fn(undefined);
    }
    const spanContext = trace.setSpan(context.active(), tracer.startSpan(name));
    return await context.with(spanContext, async () => {
      const span = trace.getSpan(spanContext);
      try {
        return await Promise.resolve(fn(span));
      } catch (error) {
        if (span && error) {
          span.recordException(error);
          span.setStatus({
            code: SpanStatusCode.ERROR,
            message: error.message || String(error),
          });
        }
        throw error;
      } finally {
        if (span) {
          span.end();
        }
      }
    });
  };
}

export async function initializeNodeTracing(serviceName, options = {}) {
  if (cachedTracing) {
    return cachedTracing;
  }
  if (asBool(process.env.N00_DISABLE_TRACING)) {
    cachedTracing = noopTracing;
    return cachedTracing;
  }

  const endpoint = normalizeGrpcEndpoint(
    options.endpoint ||
      process.env.OTEL_EXPORTER_OTLP_ENDPOINT ||
      DEFAULT_GRPC_ENDPOINT,
  );
  const service = (process.env.OTEL_SERVICE_NAME || serviceName).trim();
  const sensitive = asBool(process.env.OTEL_ENABLE_SENSITIVE_DATA);

  let NodeTracerProvider;
  let BatchSpanProcessor;
  let OTLPTraceExporter;
  let Resource;
  let SemanticResourceAttributes;
  let api;

  try {
    [
      { NodeTracerProvider },
      { BatchSpanProcessor },
      { OTLPTraceExporter },
      { Resource },
      { SemanticResourceAttributes },
      api,
    ] = await Promise.all([
      import("@opentelemetry/sdk-trace-node"),
      import("@opentelemetry/sdk-trace-base"),
      import("@opentelemetry/exporter-trace-otlp-grpc"),
      import("@opentelemetry/resources"),
      import("@opentelemetry/semantic-conventions"),
      import("@opentelemetry/api"),
    ]);
  } catch (error) {
    void error;
    cachedTracing = noopTracing;
    return cachedTracing;
  }

  const resourceAttributes = {
    [SemanticResourceAttributes.SERVICE_NAME]: service,
  };
  if (sensitive) {
    resourceAttributes["n00.observability.sensitive_data"] = 1;
  }

  const provider = new NodeTracerProvider({
    resource: new Resource(resourceAttributes),
  });

  const exporter = new OTLPTraceExporter({
    url: endpoint,
  });

  provider.addSpanProcessor(new BatchSpanProcessor(exporter));
  provider.register();

  const tracer = api.trace.getTracer(service);
  cachedTracing = {
    tracer,
    isEnabled: true,
    withSpan: createSpanRunner(api, tracer),
  };

  return cachedTracing;
}
