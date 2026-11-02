// Flujo de estados de un pedido (debe coincidir con backend/app/estados.py)
export const ORDEN = ["pendiente", "en_proceso", "enviado", "entregado"];
export const ETIQUETA = {
  pendiente: "Pendiente",
  en_proceso: "En proceso",
  enviado: "Enviado",
  entregado: "Entregado",
};
