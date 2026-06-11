"""
Tests del motor de cálculo (Milestone 0). Puro Python, sin Django.

Ejecutar:  python -m prestamo.test_engine        (desde la carpeta backend)
   o bien: python prestamo/test_engine.py

DoD (prestamo.md §1.0 / §2):
 - Todo en Decimal, prec=28.
 - Reproduce la tabla de meses 1-4 (tolerancia <= 1 peso).
 - cuota_amigo + cuota_dueno == cuota_banco.
 - saldo_amigo + saldo_dueno == saldo_banco en cada mes.
 - Abono mes 5 baja saldo y recalcula cuota a la baja (n = 44).
 - Abono antes del día 11 reduce el 2% de ese mes; después del 11 no.
 - La proyección cierra en ~0 en el mes 48 con solo cuotas normales.
"""

import os
import sys
import unittest
from datetime import date
from decimal import Decimal, getcontext

# Permitir ejecutar el archivo directamente (python prestamo/test_engine.py).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from prestamo.engine import (  # noqa: E402
    proyectar,
    cuota_francesa,
    tasa_mensual,
    resolver_mes,
    redondear,
)

TOL = Decimal("1")  # tolerancia de 1 peso por redondeo

# Config real del préstamo (prestamo.md §1).
CONFIG = {
    "capital": Decimal("45000000"),
    "ea": Decimal("0.1996"),
    "plazo": 48,
    "mes_renegociacion": 2,
    "saldo_dueno": Decimal("5000000"),
    "comision_pct": Decimal("0.02"),
}

# Tabla de validación (prestamo.md §2): meses 1-4 SIN abonos.
TABLA = {
    1: {"saldo_ini_amigo": "45000000", "dos_pct": "900000",
        "cuota_amigo": "1329824.707", "saldo_fin_amigo": "44357832.13",
        "saldo_fin_banco": "44357832.13", "aporte_dueno": "0"},
    2: {"saldo_ini_amigo": "39357832.13", "dos_pct": "787156.64",
        "cuota_amigo": "1179927.311", "saldo_fin_amigo": "38779342.21",
        "saldo_fin_banco": "43705851.13", "aporte_dueno": "149897.40"},
    3: {"saldo_ini_amigo": "38779342.21", "dos_pct": "775586.84",
        "cuota_amigo": "1179927.311", "saldo_fin_amigo": "38192012.24",
        "saldo_fin_banco": "43043907.04", "aporte_dueno": "149897.40"},
    4: {"saldo_ini_amigo": "38192012.24", "dos_pct": "763840.24",
        "cuota_amigo": "1179927.311", "saldo_fin_amigo": "37595707.12",
        "saldo_fin_banco": "42371847.60", "aporte_dueno": "149897.40"},
}


class TestEngine(unittest.TestCase):

    def setUp(self):
        self.filas = proyectar(CONFIG, abonos=[])
        self.i_m = tasa_mensual(CONFIG["ea"])

    def _fila(self, mes):
        return self.filas[mes - 1]

    def assertClose(self, actual, esperado, tol=TOL, msg=""):
        diff = abs(Decimal(actual) - Decimal(esperado))
        self.assertLessEqual(diff, tol, f"{msg}: {actual} vs {esperado} (Δ={diff})")

    # --- precisión Decimal -------------------------------------------------
    def test_precision_decimal(self):
        self.assertEqual(getcontext().prec, 28)
        for fila in self.filas:
            for tramo in ("amigo", "dueno", "banco"):
                for v in fila[tramo].values():
                    self.assertIsInstance(v, Decimal)

    # --- tabla meses 1-4 ---------------------------------------------------
    def test_reproduce_tabla_meses_1_a_4(self):
        for mes, esp in TABLA.items():
            f = self._fila(mes)
            self.assertClose(f["amigo"]["saldo_inicial"], esp["saldo_ini_amigo"],
                             msg=f"mes {mes} saldo ini amigo")
            self.assertClose(f["amigo"]["comision"], esp["dos_pct"],
                             msg=f"mes {mes} 2%")
            self.assertClose(f["amigo"]["cuota"], esp["cuota_amigo"],
                             msg=f"mes {mes} cuota amigo")
            self.assertClose(f["amigo"]["saldo_final"], esp["saldo_fin_amigo"],
                             msg=f"mes {mes} saldo fin amigo")
            self.assertClose(f["banco"]["saldo_final"], esp["saldo_fin_banco"],
                             msg=f"mes {mes} saldo fin banco")
            self.assertClose(f["dueno"]["cuota"], esp["aporte_dueno"],
                             msg=f"mes {mes} aporte dueno")

    # --- cuota_amigo + cuota_dueno == cuota_banco --------------------------
    def test_suma_cuotas_igual_cuota_banco(self):
        # Desde la renegociación (mes 2) en adelante.
        for mes in range(2, CONFIG["plazo"] + 1):
            f = self._fila(mes)
            suma = f["amigo"]["cuota"] + f["dueno"]["cuota"]
            self.assertClose(suma, f["banco"]["cuota"], tol=Decimal("0.0001"),
                             msg=f"mes {mes} suma cuotas")
        # Y la suma == cuota del banco fija (1329824.707) mientras no haya abonos.
        f2 = self._fila(2)
        self.assertClose(f2["banco"]["cuota"], "1329824.707",
                         msg="cuota banco mes 2")

    # --- saldo_amigo + saldo_dueno == saldo_banco --------------------------
    def test_suma_saldos_igual_saldo_banco(self):
        for mes in range(1, CONFIG["plazo"] + 1):
            f = self._fila(mes)
            suma_ini = f["amigo"]["saldo_inicial"] + f["dueno"]["saldo_inicial"]
            suma_fin = f["amigo"]["saldo_final"] + f["dueno"]["saldo_final"]
            self.assertEqual(suma_ini, f["banco"]["saldo_inicial"],
                             f"mes {mes} saldo ini")
            self.assertEqual(suma_fin, f["banco"]["saldo_final"],
                             f"mes {mes} saldo fin")

    # --- abono mes 5: baja saldo y recalcula cuota (n = 44) ----------------
    def test_abono_mes_5_recalcula_cuota_a_la_baja(self):
        abono = {"mes": 5, "tramo": "amigo", "monto": Decimal("5000000")}
        filas_con = proyectar(CONFIG, abonos=[abono])
        f5_base = self._fila(5)
        f5 = filas_con[4]

        saldo_post = f5["amigo"]["saldo_post_abono"]
        # n = plazo - mes + 1 = 48 - 5 + 1 = 44
        cuota_esperada = cuota_francesa(saldo_post, self.i_m, 44)
        self.assertClose(f5["amigo"]["cuota"], cuota_esperada,
                         tol=Decimal("0.01"), msg="cuota recalculada mes 5")
        # La cuota nueva debe ser MENOR que la de antes del abono.
        self.assertLess(f5["amigo"]["cuota"], f5_base["amigo"]["cuota"])
        # El saldo final tras el abono debe ser menor.
        self.assertLess(f5["amigo"]["saldo_final"], f5_base["amigo"]["saldo_final"])

    # --- 2% reducido por abono antes del día 11 ----------------------------
    def test_2pct_reducido_si_abono_antes_del_corte(self):
        f5_base = self._fila(5)["amigo"]["comision"]
        abono5 = {"mes": 5, "tramo": "amigo", "monto": Decimal("5000000")}
        f5_con = proyectar(CONFIG, abonos=[abono5])[4]["amigo"]["comision"]
        self.assertLess(f5_con, f5_base, "abono en el período debe bajar el 2%")

        # Un abono que cae en el período 6 NO debe alterar el 2% del mes 5.
        abono6 = {"mes": 6, "tramo": "amigo", "monto": Decimal("5000000")}
        f5_sin = proyectar(CONFIG, abonos=[abono6])[4]["amigo"]["comision"]
        self.assertEqual(f5_sin, f5_base, "abono del mes 6 no toca el 2% del 5")

    # --- resolver_mes: antes vs después del día 11 -------------------------
    def test_resolver_mes_dia_de_corte(self):
        primer_corte = date(2026, 1, 11)  # corte del período 1
        # Mismo mes, antes del 11 -> período 1; el 11 o después -> período 2.
        self.assertEqual(resolver_mes(date(2026, 1, 5), primer_corte), 1)
        self.assertEqual(resolver_mes(date(2026, 1, 11), primer_corte), 2)
        self.assertEqual(resolver_mes(date(2026, 1, 20), primer_corte), 2)
        # Mes de mayo (período 5 cae antes del 11; después -> período 6).
        self.assertEqual(resolver_mes(date(2026, 5, 5), primer_corte), 5)
        self.assertEqual(resolver_mes(date(2026, 5, 20), primer_corte), 6)

    # --- la proyección cierra en ~0 en el mes 48 ---------------------------
    def test_proyeccion_cierra_en_cero_mes_48(self):
        f48 = self._fila(48)
        self.assertClose(f48["banco"]["saldo_final"], "0", tol=TOL,
                         msg="saldo banco mes 48")
        self.assertClose(f48["amigo"]["saldo_final"], "0", tol=TOL,
                         msg="saldo amigo mes 48")
        self.assertClose(f48["dueno"]["saldo_final"], "0", tol=TOL,
                         msg="saldo dueno mes 48")


if __name__ == "__main__":
    unittest.main(verbosity=2)
