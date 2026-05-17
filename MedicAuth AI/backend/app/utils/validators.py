"""
Validadores robustos para solicitudes de autorización quirúrgica
"""

from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime, date


@dataclass
class ValidationResult:
    """Resultado de validación con detalle de errores"""
    valido: bool
    errores: List[str] = field(default_factory=list)
    advertencias: List[str] = field(default_factory=list)

    def agregar_error(self, msg: str):
        self.errores.append(msg)
        self.valido = False

    def agregar_advertencia(self, msg: str):
        self.advertencias.append(msg)

    @property
    def campos_faltantes_formateados(self) -> List[str]:
        """Lista lista para enviar a Notion como multi_select"""
        return self.errores[:10]


# ---------------------------------------------------------------------------
# Cédula ecuatoriana
# ---------------------------------------------------------------------------

def validar_cedula_ecuatoriana(cedula: str) -> ValidationResult:
    """
    Valida cédula ecuatoriana (10 dígitos) con algoritmo módulo 10.
    También acepta RUC de persona natural (13 dígitos, primeros 10 válidos).
    """
    result = ValidationResult(valido=True)

    if not cedula:
        result.agregar_error("Cédula: campo vacío")
        return result

    cedula = cedula.strip().replace("-", "").replace(" ", "")

    # Aceptar RUC de persona natural (13 dígitos terminados en 001)
    if len(cedula) == 13:
        if not cedula.endswith("001"):
            result.agregar_error(f"Cédula: RUC '{cedula}' no corresponde a persona natural (debe terminar en 001)")
            return result
        cedula = cedula[:10]

    if not cedula.isdigit():
        result.agregar_error(f"Cédula: solo se permiten dígitos (recibido: '{cedula}')")
        return result

    if len(cedula) != 10:
        result.agregar_error(f"Cédula: debe tener 10 dígitos (recibido: {len(cedula)})")
        return result

    provincia = int(cedula[:2])
    if not ((1 <= provincia <= 24) or provincia == 30):
        result.agregar_error(f"Cédula: código de provincia inválido ({provincia}), debe ser 01-24 o 30")
        return result

    coeficientes = [2, 1, 2, 1, 2, 1, 2, 1, 2]
    total = 0
    for i, coef in enumerate(coeficientes):
        valor = int(cedula[i]) * coef
        if valor >= 10:
            valor -= 9
        total += valor

    residuo = total % 10
    esperado = 0 if residuo == 0 else 10 - residuo
    digito_verificador = int(cedula[9])

    if digito_verificador != esperado:
        result.agregar_error(
            f"Cédula: dígito verificador incorrecto (esperado {esperado}, recibido {digito_verificador})"
        )

    return result


# ---------------------------------------------------------------------------
# Campos obligatorios
# ---------------------------------------------------------------------------

CAMPOS_REQUERIDOS = {
    "paciente_nombre": "Nombre del paciente",
    "cedula":          "Cédula de identidad",
    "edad":            "Edad del paciente",
    "numero_poliza":   "Número de póliza",
    "tipo_cirugia":    "Tipo de cirugía",
    "hospital":        "Hospital",
    "medico_tratante": "Médico tratante",
}


def validar_campos_obligatorios(campos: dict) -> ValidationResult:
    """
    Recibe un dict {campo: valor} y verifica que ninguno esté vacío.
    """
    result = ValidationResult(valido=True)

    for campo, label in CAMPOS_REQUERIDOS.items():
        valor = campos.get(campo)
        # Falsy pero permitir 0 solo para edad si se quiere — aquí edad 0 es inválida igual
        if not valor:
            result.agregar_error(f"Campo requerido vacío: {label}")

    return result


# ---------------------------------------------------------------------------
# Edad
# ---------------------------------------------------------------------------

def validar_edad(edad: Optional[int]) -> ValidationResult:
    result = ValidationResult(valido=True)

    if edad is None:
        result.agregar_error("Edad: campo vacío")
        return result

    if not isinstance(edad, int):
        result.agregar_error(f"Edad: debe ser un número entero (recibido: {edad})")
        return result

    if edad < 0 or edad > 120:
        result.agregar_error(f"Edad: valor fuera de rango ({edad}), debe estar entre 0 y 120")

    return result


# ---------------------------------------------------------------------------
# Fecha solicitada
# ---------------------------------------------------------------------------

def validar_fecha_solicitada(fecha: Optional[datetime]) -> ValidationResult:
    result = ValidationResult(valido=True)

    if fecha is None:
        result.agregar_error("Fecha solicitada: campo vacío")
        return result

    hoy = datetime.now().date()
    fecha_date = fecha.date() if isinstance(fecha, datetime) else fecha

    if fecha_date < hoy:
        result.agregar_advertencia(
            f"Fecha solicitada ({fecha_date}) es anterior a hoy — se procesará igual"
        )

    dias_futuro = (fecha_date - hoy).days
    if dias_futuro > 365:
        result.agregar_advertencia(
            f"Fecha solicitada es más de un año en el futuro ({dias_futuro} días)"
        )

    return result


# ---------------------------------------------------------------------------
# Validación completa de solicitud
# ---------------------------------------------------------------------------

def validar_solicitud_completa(solicitud) -> ValidationResult:
    """
    Valida todos los aspectos de una SolicitudAutorizacion.
    Recibe el objeto Pydantic directamente.
    """
    result = ValidationResult(valido=True)

    # 1. Campos obligatorios
    campos = {
        "paciente_nombre": solicitud.paciente_nombre,
        "cedula":          solicitud.cedula,
        "edad":            solicitud.edad,
        "numero_poliza":   solicitud.numero_poliza,
        "tipo_cirugia":    solicitud.tipo_cirugia,
        "hospital":        solicitud.hospital,
        "medico_tratante": solicitud.medico_tratante,
    }
    campos_result = validar_campos_obligatorios(campos)
    result.errores.extend(campos_result.errores)
    if campos_result.errores:
        result.valido = False

    # 2. Cédula (solo si no está vacía — el error de vacío ya se capturó arriba)
    if solicitud.cedula:
        cedula_result = validar_cedula_ecuatoriana(solicitud.cedula)
        result.errores.extend(cedula_result.errores)
        result.advertencias.extend(cedula_result.advertencias)
        if cedula_result.errores:
            result.valido = False

    # 3. Edad
    if solicitud.edad is not None:
        edad_result = validar_edad(solicitud.edad)
        result.errores.extend(edad_result.errores)
        if edad_result.errores:
            result.valido = False

    # 4. Fecha
    if solicitud.fecha_solicitada:
        fecha_result = validar_fecha_solicitada(solicitud.fecha_solicitada)
        result.errores.extend(fecha_result.errores)
        result.advertencias.extend(fecha_result.advertencias)
        if fecha_result.errores:
            result.valido = False

    # 5. Informe médico (advertencia, no error — puede llegar después)
    if not solicitud.informe_medico_url:
        result.agregar_advertencia("Sin informe médico adjunto — la IA tendrá menos contexto")

    return result