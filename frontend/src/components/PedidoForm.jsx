import { useState } from "react";
import { ETIQUETA, ORDEN } from "../estados.js";

const VACIO = { cliente: "", producto: "", cantidad: 1, precio_unitario: "" };

export default function PedidoForm({ editando, onGuardar, onCancelar, onCambiarEstado }) {
  const [form, setForm] = useState(
    editando
      ? {
          cliente: editando.cliente,
          producto: editando.producto,
          cantidad: editando.cantidad,
          precio_unitario: editando.precio_unitario,
        }
      : VACIO
  );
  const [enviando, setEnviando] = useState(false);
  const [cambiando, setCambiando] = useState(false);

  const cambiar = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  const enviar = async (e) => {
    e.preventDefault();
    setEnviando(true);
    const ok = await onGuardar({
      ...form,
      cantidad: Number(form.cantidad),
      precio_unitario: Number(form.precio_unitario),
    });
    setEnviando(false);
    if (ok && !editando) setForm(VACIO);
  };

  const moverEstado = async (nuevo) => {
    setCambiando(true);
    await onCambiarEstado(nuevo);
    setCambiando(false);
  };

  const idx = editando ? ORDEN.indexOf(editando.estado) : -1;
  const ant = ORDEN[idx - 1];
  const sig = ORDEN[idx + 1];

  return (
    <section className="card">
      <h2>{editando ? `Editar pedido #${editando.numero}` : "Nuevo pedido"}</h2>

      {editando && (
        <div className="flujo">
          <div className="flujo-titulo">Flujo del pedido</div>
          <ol className="pasos">
            {ORDEN.map((e, i) => (
              <li key={e} className={i === idx ? "actual" : i < idx ? "hecho" : ""}>
                <span className="num">{i + 1}</span>
                {ETIQUETA[e]}
              </li>
            ))}
          </ol>
          <div className="acciones">
            <button type="button" disabled={!ant || cambiando} onClick={() => moverEstado(ant)}>
              ← {ant ? `Volver a ${ETIQUETA[ant]}` : "Sin estado anterior"}
            </button>
            <button type="button" disabled={!sig || cambiando} onClick={() => moverEstado(sig)}>
              {sig ? `Avanzar a ${ETIQUETA[sig]}` : "Sin estado siguiente"} →
            </button>
          </div>
          <p className="sub">El estado se cambia de un paso en un paso; usa ← si te equivocaste.</p>
        </div>
      )}

      <form onSubmit={enviar} className="form">
        <label>
          Cliente
          <input name="cliente" value={form.cliente} onChange={cambiar} required maxLength={120} />
        </label>
        <label>
          Producto
          <input name="producto" value={form.producto} onChange={cambiar} required maxLength={120} />
        </label>
        <label>
          Cantidad
          <input name="cantidad" type="number" min="1" value={form.cantidad} onChange={cambiar} required />
        </label>
        <label>
          Precio unitario
          <input
            name="precio_unitario"
            type="number"
            min="0.01"
            step="0.01"
            value={form.precio_unitario}
            onChange={cambiar}
            required
          />
        </label>
        <div className="acciones">
          <button type="submit" className="primario" disabled={enviando}>
            {enviando ? "Guardando…" : editando ? "Guardar cambios" : "Crear pedido"}
          </button>
          {editando && (
            <button type="button" onClick={onCancelar}>
              Cerrar edición
            </button>
          )}
        </div>
      </form>
    </section>
  );
}
