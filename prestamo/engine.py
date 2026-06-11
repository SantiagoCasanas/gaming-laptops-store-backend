"""
Motor de cálculo del préstamo — Python puro, SIN Django y SIN base de datos.

Es el corazón de la app. Es dinero real: todo se maneja con `Decimal` a alta
precisión (`getcontext().prec = 28`). El redondeo a 2 decimales solo ocurre en
la capa de presentación, NUNCA en los cálculos intermedios de este módulo.

Reglas implementadas (ver prestamo.md, secciones 1 y 2):

- Sistema francés: cuota = P * i_m / (1 − (1+i_m)^(−n)).
- Tasa mensual equivalente: i_m = (1 + EA)^(1/12) − 1.
- Mes 1: un solo tramo (todo el saldo es del dueño frente al banco); el amigo
  paga la cuota completa + 2% sobre el saldo.
- Mes de renegociación (config.mes_renegociacion): el saldo se parte en dos
  deudas independientes que comparten i_m. El dueño se queda con
  `saldo_dueno`; el amigo con el remanente (saldo_banco − saldo_dueno). Cada
  tramo recalcula su subcuota sobre los meses restantes. La suma de subcuotas
  == cuota del banco.
- Comisión 2%: solo el amigo, cada corte (día 11), sobre el saldo del amigo
  VIGENTE ese día (ya descontados los abonos del período).
- Abonos: siempre a capital. El plazo se mantiene fijo en el mes `plazo`; tras
  un abono la cuota del tramo que abonó se recalcula a la baja sobre los meses
  restantes (n = plazo − mes + 1).

`proyectar(config, abonos)` devuelve la tabla mes a mes encadenada hasta el mes
`plazo`, con los saldos/cuotas de amigo, dueño y banco. Los abonos se entregan
ya resueltos al período (`mes`) al que aplican; la conversión fecha→mes vive en
`resolver_mes`, también pura y testeable.
"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal, getcontext, ROUND_HALF_UP

# Precisión alta para todos los cálculos monetarios. El redondeo a centavos es
# exclusivo de la presentación (ver `redondear`).
getcontext().prec = 28

DOS = Decimal(2)
DOCE = Decimal(12)
UNO = Decimal(1)
CERO = Decimal(0)


def _d(valor) -> Decimal:
    """Convierte a Decimal sin pasar por float (acepta str, int, Decimal)."""
    if isinstance(valor, Decimal):
        return valor
    if isinstance(valor, float):
        # Nunca debería pasar dinero como float; lo serializamos vía str para
        # no arrastrar el error binario del float.
        return Decimal(str(valor))
    return Decimal(valor)


def tasa_mensual(ea) -> Decimal:
    """i_m = (1 + EA)^(1/12) − 1, en Decimal de alta precisión."""
    ea = _d(ea)
    return (UNO + ea) ** (UNO / DOCE) - UNO


def cuota_francesa(P, i_m, n) -> Decimal:
    """Cuota del sistema francés: P * i_m / (1 − (1+i_m)^(−n)).

    P = capital, i_m = tasa mensual, n = número de cuotas restantes (entero).
    """
    P = _d(P)
    i_m = _d(i_m)
    n = int(n)
    if P <= CERO or n <= 0:
        return CERO
    if i_m == CERO:
        return P / Decimal(n)
    return P * i_m / (UNO - (UNO + i_m) ** (-n))


def redondear(valor) -> Decimal:
    """Redondea a 2 decimales con ROUND_HALF_UP. SOLO para presentación."""
    return _d(valor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def resolver_mes(fecha, fecha_primer_corte, dia_corte: int = 11) -> int:
    """Mapea la fecha de un abono al período (mes) al que aplica.

    El período `m` tiene su corte el día `dia_corte` del mes
    (fecha_primer_corte + (m−1) meses). Un abono ANTES del día de corte reduce
    el saldo de ESE período; en o después del día de corte entra al período
    siguiente.

    `fecha` y `fecha_primer_corte` son `datetime.date` (o date-like con
    .year/.month/.day). Devuelve un entero >= 1.
    """
    meses = (fecha.year - fecha_primer_corte.year) * 12 + (
        fecha.month - fecha_primer_corte.month
    )
    base = meses + 1  # fecha_primer_corte == corte del período 1
    if fecha.day >= dia_corte:
        base += 1
    return max(1, base)


def proyectar(config, abonos=None):
    """Proyecta la tabla mes a mes hasta `plazo`.

    Parámetros
    ----------
    config : dict-like con claves:
        - capital            : capital inicial (mes 0). Decimal/str/int.
        - ea                 : Tasa Efectiva Anual (opcional si se da i_m).
        - i_m                : tasa mensual (opcional; si falta se deriva de ea).
        - plazo              : número total de cuotas (p.ej. 48).
        - mes_renegociacion  : mes en que el saldo se parte en dos tramos.
        - saldo_dueno        : saldo que conserva el dueño tras renegociar.
        - comision_pct       : comisión del amigo por corte (p.ej. 0.02).
    abonos : iterable de dicts {'mes': int, 'tramo': 'amigo'|'dueno',
             'monto': Decimal/str/int}. Cada abono ya viene resuelto al período.

    Devuelve
    --------
    list[dict] : una fila por mes (1..plazo). Cada fila contiene, para
    'amigo', 'dueno' y 'banco', los campos sin redondear (Decimal):
        saldo_inicial, abono, saldo_post_abono, interes, comision (2%),
        cuota, abono_capital, saldo_final.
    """
    abonos = abonos or []

    capital = _d(config["capital"])
    plazo = int(config["plazo"])
    mes_reneg = int(config["mes_renegociacion"])
    comision_pct = _d(config["comision_pct"])
    saldo_dueno_reneg = _d(config["saldo_dueno"])

    if config.get("i_m") is not None:
        i_m = _d(config["i_m"])
    else:
        i_m = tasa_mensual(config["ea"])

    # Agrupar abonos por (mes, tramo).
    abonos_por = defaultdict(lambda: CERO)
    for a in abonos:
        clave = (int(a["mes"]), a["tramo"])
        abonos_por[clave] += _d(a["monto"])

    # Estado inicial: antes de renegociar hay un solo tramo (el préstamo
    # completo), que modelamos como el tramo 'amigo' pagando sobre el plazo
    # total desde el mes 1. El dueño aún no tiene tramo propio.
    saldo_amigo = capital
    cuota_amigo = cuota_francesa(saldo_amigo, i_m, plazo)
    saldo_dueno = CERO
    cuota_dueno = CERO

    filas = []
    for m in range(1, plazo + 1):
        meses_restantes = plazo - m + 1  # n para recálculos en el período m

        # Renegociación: al inicio del mes `mes_reneg` el saldo se parte.
        if m == mes_reneg:
            saldo_dueno = saldo_dueno_reneg
            saldo_amigo = saldo_amigo - saldo_dueno_reneg  # remanente del amigo
            cuota_amigo = cuota_francesa(saldo_amigo, i_m, meses_restantes)
            cuota_dueno = cuota_francesa(saldo_dueno, i_m, meses_restantes)

        fila = {"mes": m}
        estado = {
            "amigo": (saldo_amigo, cuota_amigo),
            "dueno": (saldo_dueno, cuota_dueno),
        }
        nuevos = {}

        for tramo, (saldo_ini, cuota_vig) in estado.items():
            abono = abonos_por.get((m, tramo), CERO)
            saldo_post = saldo_ini - abono

            # Abono => recalcular la cuota a la baja, plazo fijo.
            if abono > CERO and saldo_post > CERO:
                cuota_vig = cuota_francesa(saldo_post, i_m, meses_restantes)
            elif saldo_post <= CERO:
                cuota_vig = CERO

            # 2% solo del amigo, sobre el saldo post-abono del día de corte.
            comision = comision_pct * saldo_post if tramo == "amigo" else CERO

            interes = saldo_post * i_m if saldo_post > CERO else CERO
            abono_capital = cuota_vig - interes
            saldo_fin = saldo_post - abono_capital

            fila[tramo] = {
                "saldo_inicial": saldo_ini,
                "abono": abono,
                "saldo_post_abono": saldo_post,
                "interes": interes,
                "comision": comision,
                "cuota": cuota_vig,
                "abono_capital": abono_capital,
                "saldo_final": saldo_fin,
            }
            nuevos[tramo] = (saldo_fin, cuota_vig)

        # Banco = suma de los dos tramos.
        a, dlel = fila["amigo"], fila["dueno"]
        fila["banco"] = {
            "saldo_inicial": a["saldo_inicial"] + dlel["saldo_inicial"],
            "abono": a["abono"] + dlel["abono"],
            "saldo_post_abono": a["saldo_post_abono"] + dlel["saldo_post_abono"],
            "interes": a["interes"] + dlel["interes"],
            "comision": a["comision"] + dlel["comision"],
            "cuota": a["cuota"] + dlel["cuota"],
            "abono_capital": a["abono_capital"] + dlel["abono_capital"],
            "saldo_final": a["saldo_final"] + dlel["saldo_final"],
        }

        filas.append(fila)

        # Avanzar estado.
        saldo_amigo, cuota_amigo = nuevos["amigo"]
        saldo_dueno, cuota_dueno = nuevos["dueno"]

    return filas
