from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

Estado = Literal["pendiente", "en_proceso", "enviado", "entregado"]


class PedidoIn(BaseModel):
    cliente: str = Field(min_length=1, max_length=120)
    producto: str = Field(min_length=1, max_length=120)
    cantidad: int = Field(gt=0, le=100000)
    precio_unitario: Decimal = Field(gt=0, max_digits=10, decimal_places=2)


class PedidoUpdate(PedidoIn):
    version: int = Field(ge=1, description="Versión leída por el cliente (control optimista)")


class EstadoUpdate(BaseModel):
    estado: Estado
    version: int = Field(ge=1)


class PedidoOut(BaseModel):
    id: int          # identificador interno (se usa en las rutas de la API)
    numero: int      # posición por orden de llegada entre los pedidos vigentes: 1, 2, 3…
    cliente: str
    producto: str
    cantidad: int
    precio_unitario: float
    total: float
    estado: Estado
    version: int
    created_at: datetime
    updated_at: datetime
