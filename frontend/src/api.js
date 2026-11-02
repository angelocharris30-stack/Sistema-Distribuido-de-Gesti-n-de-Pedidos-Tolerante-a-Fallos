// Cliente REST con reintentos automáticos ante fallos de red / 502 / 504.
// Las peticiones POST llevan una Idempotency-Key fija entre reintentos,
// por lo que un reintento nunca duplica un pedido.

const RETRY_STATUS = [502, 504];
const MAX_REINTENTOS = 3;
const espera = (ms) => new Promise((r) => setTimeout(r, ms));

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

async function request(path, { method = "GET", body, headers = {} } = {}) {
  let ultimoError;
  for (let intento = 0; intento <= MAX_REINTENTOS; intento++) {
    const t0 = performance.now();
    try {
      const res = await fetch(`/api${path}`, {
        method,
        headers: { "Content-Type": "application/json", ...headers },
        body: body ? JSON.stringify(body) : undefined,
      });
      if (RETRY_STATUS.includes(res.status) && intento < MAX_REINTENTOS) {
        await espera(500 * (intento + 1));
        continue;
      }
      const meta = {
        node: res.headers.get("X-Node-Id") || "?",
        ms: Math.round(performance.now() - t0),
        intentos: intento + 1,
      };
      if (res.status === 204) return { data: null, meta };
      const data = await res.json().catch(() => null);
      if (!res.ok) {
        const detalle = Array.isArray(data?.detail)
          ? data.detail.map((d) => d.msg).join("; ")
          : data?.detail || `Error ${res.status}`;
        throw new ApiError(detalle, res.status);
      }
      return { data, meta };
    } catch (e) {
      if (e instanceof ApiError) throw e;
      ultimoError = e;
      if (intento < MAX_REINTENTOS) await espera(500 * (intento + 1));
    }
  }
  throw new ApiError("Sin conexión con el sistema (todos los nodos caídos o red no disponible).", 0);
}

const nuevaClave = () =>
  (crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`);

export const api = {
  listar: (estado, consistente = false) => {
    const q = new URLSearchParams();
    if (estado) q.set("estado", estado);
    if (consistente) q.set("consistent", "true"); // leer del primario (read-your-writes)
    const qs = q.toString();
    return request(`/pedidos${qs ? `?${qs}` : ""}`);
  },
  crear: (pedido, clave = nuevaClave()) =>
    request("/pedidos", { method: "POST", body: pedido, headers: { "Idempotency-Key": clave } }),
  actualizar: (id, pedido) => request(`/pedidos/${id}`, { method: "PUT", body: pedido }),
  cambiarEstado: (id, estado, version) =>
    request(`/pedidos/${id}/estado`, { method: "PATCH", body: { estado, version } }),
  eliminar: (id) => request(`/pedidos/${id}`, { method: "DELETE" }),
  cluster: () => request("/cluster"),
};
