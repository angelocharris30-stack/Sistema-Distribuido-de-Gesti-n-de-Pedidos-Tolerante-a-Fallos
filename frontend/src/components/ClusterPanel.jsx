import { useEffect, useState } from "react";
import { api } from "../api.js";

function Tarjeta({ titulo, subtitulo, up, detalle }) {
  return (
    <div className={`nodo-card ${up ? "up" : "down"}`}>
      <div className="semaforo" />
      <div>
        <b>{titulo}</b>
        <div className="sub">{subtitulo}</div>
        <div className="det">{up ? detalle || "operativo" : detalle || "sin respuesta"}</div>
      </div>
    </div>
  );
}

export default function ClusterPanel() {
  const [estado, setEstado] = useState(null);
  const [caido, setCaido] = useState(false);
  const [ultima, setUltima] = useState("");

  useEffect(() => {
    let vivo = true;
    const consultar = async () => {
      try {
        const { data } = await api.cluster();
        if (vivo) {
          setEstado(data);
          setCaido(false);
          setUltima(new Date().toLocaleTimeString());
        }
      } catch {
        if (vivo) setCaido(true);
      }
    };
    consultar();
    const t = setInterval(consultar, 2000);
    return () => {
      vivo = false;
      clearInterval(t);
    };
  }, []);

  return (
    <main className="monitor">
      <section className="card">
        <h2>Monitoreo del clúster</h2>
        <p className="sub">
          Actualización cada 2 s{ultima && ` · última: ${ultima}`}
          {estado && ` · consulta atendida por ${estado.answered_by}`}
        </p>
        {caido && (
          <div className="banner error">
            ⚠ No hay respuesta del balanceador / nodos de aplicación.
          </div>
        )}

        <h3>Balanceador</h3>
        <div className="grid">
          <Tarjeta titulo="NGINX gateway" subtitulo="punto de entrada :8080" up={!caido} />
        </div>

        <h3>Nodos de aplicación (FastAPI)</h3>
        <div className="grid">
          {estado?.api_nodes.map((n) => (
            <Tarjeta key={n.node} titulo={n.node} subtitulo={n.url} up={n.up} />
          ))}
        </div>

        <h3>Nodos de base de datos (PostgreSQL)</h3>
        <div className="grid">
          {estado?.db_nodes.map((d) => (
            <Tarjeta
              key={d.host}
              titulo={d.host}
              subtitulo={d.up ? (d.role === "primary" ? "PRIMARIO (lectura/escritura)" : "RÉPLICA (solo lectura)") : "caído"}
              up={d.up}
              detalle={d.detail}
            />
          ))}
        </div>
      </section>
    </main>
  );
}
