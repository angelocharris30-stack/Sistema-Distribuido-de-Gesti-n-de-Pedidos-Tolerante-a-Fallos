import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api.js";
import PedidoForm from "./components/PedidoForm.jsx";
import PedidoTable from "./components/PedidoTable.jsx";
import ClusterPanel from "./components/ClusterPanel.jsx";

export default function App() {
  const [tab, setTab] = useState("pedidos");
  const [pedidos, setPedidos] = useState([]);
  const [filtro, setFiltro] = useState("");
  const [editando, setEditando] = useState(null);
  const [error, setError] = useState("");
  const [aviso, setAviso] = useState(null); // { id, texto } -> notificación flotante de 1,5 s
  const avisoTimer = useRef(null);
  const [meta, setMeta] = useState(null);
  const [cargando, setCargando] = useState(true);

  const cargar = useCallback(async (consistente = false) => {
    try {
      const { data, meta } = await api.listar(filtro, consistente === true);
      setPedidos(data);
      setMeta(meta);
      setError("");
    } catch (e) {
      setError(e.message);
    } finally {
      setCargando(false);
    }
  }, [filtro]);

  useEffect(() => {
    cargar();
    const t = setInterval(() => cargar(), 5000); // refresco periódico: se ve la conmutación en vivo
    return () => clearInterval(t);
  }, [cargar]);

  const mostrarAviso = (texto) => {
    clearTimeout(avisoTimer.current);
    setAviso({ id: Date.now(), texto }); // el id reinicia la animación si llega otro aviso
    avisoTimer.current = setTimeout(() => setAviso(null), 1500);
  };

  // Ejecuta una acción de escritura mostrando errores y refrescando la lista.
  // Devuelve { data } si salió bien o null si falló.
  const ejecutar = async (fn, mensajeOk) => {
    try {
      const { data, meta } = await fn();
      setMeta(meta);
      setError("");
      mostrarAviso(mensajeOk);
      await cargar(true); // tras escribir, leer del primario
      return { data };
    } catch (e) {
      setError(e.message);
      if (e.status === 409) cargar(true); // conflicto: traer la versión actual
      return null;
    }
  };

  const guardar = async (form) => {
    if (editando) {
      const r = await ejecutar(
        () => api.actualizar(editando.id, { ...form, version: editando.version }),
        `Pedido #${editando.numero} actualizado`
      );
      if (r) setEditando(null);
      return !!r;
    }
    return !!(await ejecutar(() => api.crear(form), "Pedido creado"));
  };

  // Cambio de estado desde el formulario de edición (avanzar o retroceder un paso)
  const cambiarEstado = async (nuevo) => {
    const r = await ejecutar(
      () => api.cambiarEstado(editando.id, nuevo, editando.version),
      `Pedido #${editando.numero}: ${editando.estado} → ${nuevo}`
    );
    if (r) setEditando({ ...editando, estado: r.data.estado, version: r.data.version });
  };

  // El número visible puede cambiar si se elimina otro pedido: se toma siempre de la lista actual
  const editandoVista = editando
    ? { ...editando, numero: pedidos.find((x) => x.id === editando.id)?.numero ?? editando.numero }
    : null;

  const iniciarEdicion = (p) => {
    setEditando(p);
    window.scrollTo({ top: 0, behavior: "smooth" }); // llevar al formulario de arriba
  };

  return (
    <div className="app">
      <header>
        <h1>Gestión Distribuida de Pedidos</h1>
        <nav>
          <button className={tab === "pedidos" ? "on" : ""} onClick={() => setTab("pedidos")}>
            Pedidos
          </button>
          <button className={tab === "monitor" ? "on" : ""} onClick={() => setTab("monitor")}>
            Monitoreo del clúster
          </button>
        </nav>
        {meta && (
          <span className="nodo">
            Atendido por <b>{meta.node}</b> · {meta.ms} ms
            {meta.intentos > 1 && ` · ${meta.intentos} intentos`}
          </span>
        )}
      </header>

      {/* Notificaciones flotantes: no desplazan el contenido de la página */}
      <div className="toasts" aria-live="polite">
        {error && <div className="toast error">⚠ {error}</div>}
        {aviso && (
          <div key={aviso.id} className="toast ok">
            ✔ {aviso.texto}
          </div>
        )}
      </div>

      {tab === "pedidos" ? (
        <main>
          <PedidoForm
            key={editando ? editando.id : "nuevo"}
            editando={editandoVista}
            onGuardar={guardar}
            onCancelar={() => setEditando(null)}
            onCambiarEstado={cambiarEstado}
          />
          <section className="card">
            <div className="fila-titulo">
              <h2>Pedidos</h2>
              <select value={filtro} onChange={(e) => setFiltro(e.target.value)}>
                <option value="">Todos los estados</option>
                <option value="pendiente">Pendiente</option>
                <option value="en_proceso">En proceso</option>
                <option value="enviado">Enviado</option>
                <option value="entregado">Entregado</option>
              </select>
            </div>
            <PedidoTable
              pedidos={pedidos}
              cargando={cargando}
              editandoId={editando ? editando.id : null}
              onEditar={iniciarEdicion}
              onEliminar={(p) => {
                if (confirm(`¿Eliminar el pedido #${p.numero}?`)) {
                  if (editando && editando.id === p.id) setEditando(null);
                  ejecutar(() => api.eliminar(p.id), `Pedido #${p.numero} eliminado`);
                }
              }}
            />
          </section>
        </main>
      ) : (
        <ClusterPanel />
      )}
    </div>
  );
}
