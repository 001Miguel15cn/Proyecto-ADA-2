"""
bb_manual.py - Branch and Bound didactico sobre la instancia reducida.
Resuelve cada relajacion lineal con CBC (via PuLP) y arma el arbol (mejor cota primero).
necesario para VERIFICAR el ejercicio hecho a mano en el informe.
"""
from pathlib import Path
import heapq
import math
import sys
import pulp

BASE_DIR = Path(__file__).resolve().parent
CARPETA_MODELO = BASE_DIR.parent / "Modelo"

if str(CARPETA_MODELO) not in sys.path:
    sys.path.insert(0, str(CARPETA_MODELO))

import optimizador as o

# Si instancia_bb.json está en la misma carpeta que bb_manual.py:
ruta_instancia = BASE_DIR / "instancia_bb.json"
# (Si está dentro de Modelo/, cambia la línea anterior por:
#  ruta_instancia = CARPETA_MODELO / "instancia_bb.json")

esc = o.cargar_json(ruta_instancia)

def lp_nodo(cotas):
    prob, ctx = o.construir_modelo(esc)
    for v in prob.variables():
        v.cat = pulp.LpContinuous
    for (c, z, k), v in ctx["x"].items():
        lo, hi = cotas.get(v.name, (None, None))
        if lo is not None: v.lowBound = lo
        if hi is not None: v.upBound = hi
    prob.solve(pulp.PULP_CBC_CMD(msg=False))
    if pulp.LpStatus[prob.status] != "Optimal":
        return None, None
    return pulp.value(prob.objective), {v.name: v.varValue for v in ctx["x"].values()}

def fraccionaria(sol):
    cand = [(abs(v - round(v)), n, v) for n, v in sol.items() if abs(v - round(v)) > 1e-6]
    return max(cand)[1:] if cand else None

incumbente, mejor_sol, contador = -math.inf, None, 0
z0, s0 = lp_nodo({})
heap = [(-z0, 0, {}, s0, "P0")]
print(f"{'Nodo':<8}{'Subproblema':<34}{'Z_LP':>8}  Resultado")
while heap:
    negz, _, cotas, sol, nombre = heapq.heappop(heap)
    z = -negz
    desc = ", ".join(f"{n.replace('x_C1_','')} {'<=' if t=='U' else '>='} {int(b)}"
                     for n, (t, b) in [(n, (('U', hi) if hi is not None else ('L', lo))) for n, (lo, hi) in
                     [(k, v) for k, v in cotas.items()] ] ) if False else str(
        {k.replace('x_C1_',''): v for k, v in cotas.items()})
    if z <= incumbente + 1e-9:
        print(f"{nombre:<8}{desc:<34}{z:8.4f}  PODA por cota ({z:.4f} <= incumbente {incumbente:.4f})")
        continue
    f = fraccionaria(sol)
    if f is None:
        incumbente, mejor_sol = z, sol
        print(f"{nombre:<8}{desc:<34}{z:8.4f}  ENTERA -> nuevo incumbente {z:.4f}  {({k.replace('x_C1_',''):v for k,v in sol.items() if v>1e-9})}")
        continue
    nom, val = f
    print(f"{nombre:<8}{desc:<34}{z:8.4f}  fraccionaria {nom.replace('x_C1_','')}={val:.4f} -> ramificar")
    for lado, (lo, hi) in (("a", (None, math.floor(val))), ("b", (math.ceil(val), None))):
        nuevo = dict(cotas)
        l0, h0 = nuevo.get(nom, (None, None))
        nuevo[nom] = (lo if lo is not None else l0, hi if hi is not None else h0)
        zz, ss = lp_nodo(nuevo)
        contador += 1
        nm = f"{nombre[:-0 or None]}.{lado}" if nombre != "P0" else f"P{lado}"
        if zz is None:
            print(f"{nm:<8}{str({k.replace('x_C1_',''):v for k,v in nuevo.items()}):<34}{'--':>8}  PODA por infactibilidad")
            continue
        heapq.heappush(heap, (-zz, contador, nuevo, ss, nm))
print("\nOptimo entero:", incumbente, {k.replace('x_C1_',''): v for k, v in mejor_sol.items() if v > 1e-9})
