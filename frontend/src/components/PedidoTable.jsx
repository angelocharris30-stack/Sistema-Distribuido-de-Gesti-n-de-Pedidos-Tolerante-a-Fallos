import { ETIQUETA } from "../estados.js";

const moneda = (n) => n.toLocaleString("es-CO", { style: "currency", currency: "COP", maximumFractionDigits: 0 });

export default function PedidoTable({ pedidos, cargando, editandoId, onEditar, onEliminar }) {
  if (cargando) return <p className="vacio">Cargando…</p>;
  if (!pedidos.length) return <p className="vacio">No hay pedidos para mostrar.</p>;

  return (
    <div className="tabla-wrap">
      <table>
        <thead>
          <tr>
            <th>#</th>
            <th>Cliente</th>
            <th>Producto</th>
            <th>Cant.</th>
            <th>Total</th>
            <th>Estado</th>
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody>
          {pedidos.map((p) => (
            <tr key={p.id} className={p.id === editandoId ? "fila-editando" : ""}>
              <td>{p.numero}</td>
              <td>{p.cliente}</td>
              <td>{p.producto}</td>
              <td>{p.cantidad}</td>
              <td>{moneda(p.total)}</td>
              <td>
                <span className={`chip ${p.estado}`}>{ETIQUETA[p.estado]}</span>
              </td>
              <td className="acciones">
                <button onClick={() => onEditar(p)}>Editar</button>
                <button className="peligro" onClick={() => onEliminar(p)}>
                  Eliminar
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
