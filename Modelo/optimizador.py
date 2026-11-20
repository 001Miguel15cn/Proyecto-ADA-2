"""
optimizador.py
==============
Modelo matematico y ejecucion del solver para el Sistema de Optimizacion de
Distribucion de Ayudas Humanitarias (Proyecto final ADA II).

Flujo:  Escenario (dict/JSON) -> validar -> construir modelo (PuLP) -> CBC
        -> interpretar solucion -> Resultado (dict)

Este modulo NO depende de la interfaz grafica: recibe un diccionario y devuelve
un diccionario, de modo que la GUI (otro integrante) solo lo invoca.

Formato del escenario (todas las claves son parametrizables, nada esta fijo):
{
  "tipos_ayuda":  [{"id": "agua", "divisible": false, "volumen": 1.0, "importancia": 1.0}],
  "prioridades":  {"Critica": 4, "Alta": 3, "Media": 2, "Baja": 1},
  "centros":      [{"id": "C1", "activo": true, "cap_despacho": 100,
                    "inventario": {"agua": 50}, "reserva": {"agua": 0}}],
  "zonas":        [{"id": "Z1", "poblacion": 1000, "prioridad": "Alta",
                    "demanda": {"agua": 40}, "cobertura_minima": 0.0}],
  "rutas":        [{"origen": "C1", "destino": "Z1", "disponible": true,
                    "costo": 2.0, "capacidad": 60}],
  "incompatibilidades": [{"centro": "C1", "ayuda": "agua"}],      # opcional
  "opciones": {"ponderar_por_poblacion": false}                   # opcional
}
"""
from __future__ import annotations
from pathlib import Path

import json
import math
import time
from typing import Any

import pulp

TOL = 1e-6

def cargar_json(ruta: str | Path) -> dict:
    p = Path(ruta)
    if not p.is_absolute() and not p.exists():
        candidata = Path(__file__).resolve().parent / p
        if candidata.exists():
            p = candidata
    with open(p, encoding="utf-8") as f:
        return json.load(f)
    
# ---------------------------------------------------------------------------
# 1. VALIDACION
# ---------------------------------------------------------------------------
def validar_escenario(esc: dict) -> list[str]:
    """Devuelve una lista de errores comprensibles (vacia si todo es valido)."""
    err: list[str] = []

    def num_ok(v, nombre, minimo=0.0):
        if not isinstance(v, (int, float)) or isinstance(v, bool) or math.isnan(v):
            err.append(f"{nombre}: debe ser un numero (recibido: {v!r}).")
            return False
        if v < minimo:
            err.append(f"{nombre}: no puede ser menor que {minimo} (recibido: {v}).")
            return False
        return True

    for clave in ("tipos_ayuda", "prioridades", "centros", "zonas", "rutas"):
        if clave not in esc:
            err.append(f"Falta la seccion obligatoria '{clave}'.")
    if err:
        return err

    def ids_unicos(lista, etiqueta):
        vistos = set()
        for e in lista:
            i = e.get("id")
            if i in (None, ""):
                err.append(f"{etiqueta}: hay un elemento sin identificador.")
            elif i in vistos:
                err.append(f"{etiqueta}: identificador repetido '{i}'.")
            vistos.add(i)
        return vistos

    tipos = ids_unicos(esc["tipos_ayuda"], "Tipos de ayuda")
    centros = ids_unicos(esc["centros"], "Centros")
    zonas = ids_unicos(esc["zonas"], "Zonas")

    if not esc["tipos_ayuda"]:
        err.append("Debe existir al menos un tipo de ayuda.")
    if not any(c.get("activo", True) for c in esc["centros"]):
        err.append("No hay ningun centro activo.")
    if not esc["zonas"]:
        err.append("Debe existir al menos una zona afectada.")

    for p, w in esc["prioridades"].items():
        num_ok(w, f"Peso de la prioridad '{p}'", 0.0)
        if isinstance(w, (int, float)) and w <= 0:
            err.append(f"Peso de la prioridad '{p}': debe ser estrictamente positivo.")

    for t in esc["tipos_ayuda"]:
        num_ok(t.get("volumen", 1.0), f"Volumen del tipo '{t.get('id')}'", 0.0)
        if t.get("volumen", 1.0) == 0:
            err.append(f"Volumen del tipo '{t.get('id')}': debe ser > 0.")
        num_ok(t.get("importancia", 1.0), f"Importancia del tipo '{t.get('id')}'", 0.0)

    for c in esc["centros"]:
        cid = c.get("id")
        num_ok(c.get("cap_despacho", 0), f"Capacidad de despacho del centro '{cid}'")
        for k, q in c.get("inventario", {}).items():
            if k not in tipos:
                err.append(f"Centro '{cid}': tipo de ayuda desconocido '{k}' en inventario.")
            num_ok(q, f"Inventario de '{k}' en centro '{cid}'")
        for k, q in c.get("reserva", {}).items():
            if k not in tipos:
                err.append(f"Centro '{cid}': tipo de ayuda desconocido '{k}' en reserva.")
            if num_ok(q, f"Reserva de '{k}' en centro '{cid}'"):
                if q > c.get("inventario", {}).get(k, 0):
                    err.append(f"Centro '{cid}': la reserva de '{k}' ({q}) supera su inventario.")

    for z in esc["zonas"]:
        zid = z.get("id")
        if z.get("prioridad") not in esc["prioridades"]:
            err.append(f"Zona '{zid}': prioridad '{z.get('prioridad')}' no esta definida.")
        num_ok(z.get("poblacion", 0), f"Poblacion de la zona '{zid}'")
        for k, q in z.get("demanda", {}).items():
            if k not in tipos:
                err.append(f"Zona '{zid}': tipo de ayuda desconocido '{k}' en demanda.")
            num_ok(q, f"Demanda de '{k}' en zona '{zid}'")
        b = z.get("cobertura_minima", 0.0)
        if num_ok(b, f"Cobertura minima de la zona '{zid}'") and b > 1:
            err.append(f"Zona '{zid}': la cobertura minima debe estar entre 0 y 1 (recibido {b}).")

    vistas = set()
    for r in esc["rutas"]:
        o, d = r.get("origen"), r.get("destino")
        if o not in centros:
            err.append(f"Ruta {o}->{d}: el centro de origen no existe.")
        if d not in zonas:
            err.append(f"Ruta {o}->{d}: la zona de destino no existe.")
        if (o, d) in vistas:
            err.append(f"Ruta {o}->{d}: esta definida mas de una vez.")
        vistas.add((o, d))
        num_ok(r.get("costo", 0), f"Costo de la ruta {o}->{d}")
        num_ok(r.get("capacidad", 0), f"Capacidad de la ruta {o}->{d}")

    for inc in esc.get("incompatibilidades", []):
        if inc.get("centro") not in centros or inc.get("ayuda") not in tipos:
            err.append(f"Incompatibilidad invalida: {inc}.")
    return err


# ---------------------------------------------------------------------------
# 2. CONSTRUCCION DEL MODELO
# ---------------------------------------------------------------------------
def construir_modelo(esc: dict) -> tuple[pulp.LpProblem, dict]:
    """
    Construye el modelo PLE/PLEM a partir del escenario ya validado.
    Devuelve (problema, contexto) donde contexto guarda variables y parametros.
    """
    opciones = esc.get("opciones", {})
    K = [t["id"] for t in esc["tipos_ayuda"]]
    tipo = {t["id"]: t for t in esc["tipos_ayuda"]}
    C = [c["id"] for c in esc["centros"]]
    cen = {c["id"]: c for c in esc["centros"]}
    Z = [z["id"] for z in esc["zonas"]]
    zon = {z["id"]: z for z in esc["zonas"]}

    # ---- Parametros ------------------------------------------------------
    vol = {k: float(tipo[k].get("volumen", 1.0)) for k in K}          # v_k
    imp = {k: float(tipo[k].get("importancia", 1.0)) for k in K}      # pi_k
    ent = {k: not bool(tipo[k].get("divisible", True)) for k in K}    # I_k (indivisible)

    inv = {(c, k): float(cen[c].get("inventario", {}).get(k, 0)) for c in C for k in K}
    res = {(c, k): float(cen[c].get("reserva", {}).get(k, 0)) for c in C for k in K}
    act = {c: bool(cen[c].get("activo", True)) for c in C}
    D = {c: float(cen[c].get("cap_despacho", 0)) for c in C}

    dem = {(z, k): float(zon[z].get("demanda", {}).get(k, 0)) for z in Z for k in K}
    beta = {z: float(zon[z].get("cobertura_minima", 0.0)) for z in Z}
    pesos_prio = esc["prioridades"]
    w = {z: float(pesos_prio[zon[z]["prioridad"]]) for z in Z}
    if opciones.get("ponderar_por_poblacion", False):
        pob = {z: float(zon[z].get("poblacion", 0)) for z in Z}
        media = sum(pob.values()) / len(Z) if sum(pob.values()) > 0 else 1.0
        W = {z: w[z] * (pob[z] / media if media > 0 else 1.0) for z in Z}
    else:
        W = dict(w)

    # Conjunto de rutas utilizables A: existe, esta disponible y capacidad > 0
    rutas = {}
    for r in esc["rutas"]:
        if r.get("disponible", True) and float(r.get("capacidad", 0)) > 0:
            rutas[(r["origen"], r["destino"])] = r
    cost = {a: float(r.get("costo", 0)) for a, r in rutas.items()}    # c_cz
    cap = {a: float(r.get("capacidad", 0)) for a, r in rutas.items()} # u_cz
    incomp = {(i["centro"], i["ayuda"]) for i in esc.get("incompatibilidades", [])}

    # Beneficio unitario normalizado:  b_zk = W_z * pi_k / d_zk
    b = {(z, k): (W[z] * imp[k] / dem[z, k]) for z in Z for k in K if dem[z, k] > 0}

    # Peso del costo (epsilon): garantiza que el costo solo desempata.
    c_max = max(cost.values(), default=0.0)
    b_min = min(b.values(), default=1.0)
    eps = 0.01 * b_min / c_max if c_max > 0 else 0.0

    # Indices validos de la variable x_{czk}
    idx = [
        (c, z, k)
        for (c, z) in rutas
        for k in K
        if act[c] and dem[z, k] > 0 and inv[c, k] - res[c, k] > TOL and (c, k) not in incomp
    ]

    # ---- Modelo ----------------------------------------------------------
    prob = pulp.LpProblem("Distribucion_Ayudas_Humanitarias", pulp.LpMaximize)

    x = {
        (c, z, k): pulp.LpVariable(
            f"x_{c}_{z}_{k}", lowBound=0, cat=pulp.LpInteger if ent[k] else pulp.LpContinuous
        )
        for (c, z, k) in idx
    }
    s = {
        (z, k): pulp.LpVariable(
            f"s_{z}_{k}", lowBound=0, upBound=dem[z, k],
            cat=pulp.LpInteger if ent[k] else pulp.LpContinuous,
        )
        for z in Z for k in K if dem[z, k] > 0
    }

    # Funcion objetivo:  max  sum b_zk * (d_zk - s_zk)  -  eps * sum c_cz x_czk
    prob += (
        pulp.lpSum(b[z, k] * (dem[z, k] - s[z, k]) for (z, k) in s)
        - eps * pulp.lpSum(cost[c, z] * x[c, z, k] for (c, z, k) in x),
        "Cobertura_ponderada_menos_costo",
    )

    # R1. Balance de demanda: lo atendido + lo no atendido = demanda  (R5 y R6)
    for (z, k) in s:
        enviado = pulp.lpSum(x[c, zz, kk] for (c, zz, kk) in x if zz == z and kk == k)
        prob += enviado + s[z, k] == dem[z, k], f"Balance_{z}_{k}"

    # R2. Inventario disponible (descontando reserva)  (R1 y adicional A1)
    for c in C:
        for k in K:
            env = [x[c, z, k] for (cc, z, kk) in x if cc == c and kk == k]
            if env:
                prob += pulp.lpSum(env) <= inv[c, k] - res[c, k], f"Inventario_{c}_{k}"

    # R3. Capacidad de despacho del centro (en unidades de carga)   (R2)
    for c in C:
        env = [vol[k] * x[c, z, k] for (cc, z, k) in x if cc == c]
        if env:
            prob += pulp.lpSum(env) <= D[c], f"Despacho_{c}"

    # R4. Capacidad de la ruta (en unidades de carga)                (R3)
    for (c, z) in rutas:
        env = [vol[k] * x[c, z, k] for (cc, zz, k) in x if cc == c and zz == z]
        if env:
            prob += pulp.lpSum(env) <= cap[c, z], f"Ruta_{c}_{z}"

    # A2. Cobertura minima por zona y tipo de ayuda
    for (z, k) in s:
        if beta[z] > 0:
            minimo = beta[z] * dem[z, k]
            if ent[k]:
                minimo = math.ceil(minimo - TOL)
            prob += dem[z, k] - s[z, k] >= minimo, f"CobMin_{z}_{k}"

    # Rutas bloqueadas (R4), no negatividad (R8), enteras (R9) y multiples
    # tipos (R10) quedan garantizadas por construccion: no se crean variables
    # sobre rutas bloqueadas, lowBound=0, cat=Integer para ayudas indivisibles
    # y el indice k recorre todos los tipos simultaneamente.

    ctx = dict(K=K, C=C, Z=Z, x=x, s=s, dem=dem, inv=inv, res=res, cost=cost, cap=cap,
               vol=vol, W=W, w=w, b=b, eps=eps, ent=ent, rutas=rutas, D=D, beta=beta,
               imp=imp, cen=cen, zon=zon)
    return prob, ctx


# ---------------------------------------------------------------------------
# 3. SOLVER
# ---------------------------------------------------------------------------
def resolver(prob: pulp.LpProblem, tiempo_limite: float | None = 60,
             gap_rel: float = 0.0, mensajes: bool = False) -> dict:
    """Ejecuta CBC y devuelve estado, tiempo y tamano del modelo."""
    solver = pulp.PULP_CBC_CMD(msg=mensajes, timeLimit=tiempo_limite, gapRel=gap_rel)
    t0 = time.perf_counter()
    prob.solve(solver)
    dt = time.perf_counter() - t0
    return {
        "estado": pulp.LpStatus[prob.status],
        "tiempo_s": dt,
        "n_variables": len(prob.variables()),
        "n_variables_enteras": sum(1 for v in prob.variables() if v.cat == pulp.LpInteger),
        "n_restricciones": len(prob.constraints),
        "valor_objetivo": pulp.value(prob.objective),
    }


# ---------------------------------------------------------------------------
# 4. INTERPRETACION
# ---------------------------------------------------------------------------
def interpretar(ctx: dict, info: dict) -> dict:
    """Convierte los valores de las variables en los indicadores del enunciado (sec. 12)."""
    K, C, Z = ctx["K"], ctx["C"], ctx["Z"]
    x, dem, vol = ctx["x"], ctx["dem"], ctx["vol"]
    val = lambda v: max(0.0, round(v.value() or 0.0, 6))

    envios = {a: val(v) for a, v in x.items() if val(v) > TOL}          # (c,z,k) -> cantidad
    enviado_zk = {(z, k): sum(q for (c, zz, kk), q in envios.items() if zz == z and kk == k)
                  for z in Z for k in K}
    atendida = {(z, k): enviado_zk[z, k] for z in Z for k in K if dem[z, k] > 0}
    no_atendida = {zk: dem[zk] - q for zk, q in atendida.items()}

    dem_total = sum(dem[zk] for zk in atendida)
    cobertura_global = 100 * sum(atendida.values()) / dem_total if dem_total else 100.0
    # Cobertura ponderada (la que realmente maximiza el modelo), en %
    cob_pond = None
    if ctx["b"]:
        num = sum(ctx["b"][zk] * atendida[zk] for zk in atendida)
        den = sum(ctx["b"][zk] * dem[zk] for zk in atendida)
        cob_pond = 100 * num / den if den else 100.0

    def pct(num, den):
        return 100 * num / den if den else None

    cob_zona = {z: pct(sum(atendida[z, k] for k in K if (z, k) in atendida),
                       sum(dem[z, k] for k in K if (z, k) in atendida)) for z in Z}
    cob_tipo = {k: pct(sum(atendida[z, k] for z in Z if (z, k) in atendida),
                       sum(dem[z, k] for z in Z if (z, k) in atendida)) for k in K}
    cob_zona_tipo = {zk: pct(atendida[zk], dem[zk]) for zk in atendida}

    enviado_centro = {c: {k: sum(q for (cc, z, kk), q in envios.items() if cc == c and kk == k)
                          for k in K} for c in C}
    recibido_zona = {z: {k: enviado_zk[z, k] for k in K} for z in Z}
    inv_restante = {c: {k: ctx["inv"][c, k] - enviado_centro[c][k] for k in K} for c in C}
    carga_centro = {c: sum(vol[k] * enviado_centro[c][k] for k in K) for c in C}

    rutas_usadas = {}
    for (c, z, k), q in envios.items():
        r = rutas_usadas.setdefault((c, z), {"carga": 0.0, "costo": 0.0, "detalle": {}})
        r["carga"] += vol[k] * q
        r["costo"] += ctx["cost"][c, z] * q
        r["detalle"][k] = q
    costo_total = sum(ctx["cost"][c, z] * q for (c, z, k), q in envios.items())

    return {
        **info,
        "cobertura_global_pct": cobertura_global,
        "cobertura_ponderada_pct": cob_pond,
        "cobertura_por_zona_pct": cob_zona,
        "cobertura_por_tipo_pct": cob_tipo,
        "cobertura_zona_tipo_pct": cob_zona_tipo,
        "envios": envios,                          # {(centro, zona, tipo): cantidad}
        "enviado_por_centro": enviado_centro,
        "recibido_por_zona": recibido_zona,
        "demanda_atendida": atendida,
        "demanda_no_atendida": no_atendida,
        "rutas_usadas": rutas_usadas,
        "costo_total": costo_total,
        "inventario_restante": inv_restante,
        "carga_despachada_por_centro": carga_centro,
        "epsilon": ctx["eps"],
    }


# ---------------------------------------------------------------------------
# 5. FUNCION DE ALTO NIVEL (la que llama la GUI)
# ---------------------------------------------------------------------------
def optimizar(escenario: dict, tiempo_limite: float | None = 60, gap_rel: float = 0.0,
              exportar_lp: str | None = None, mensajes_solver: bool = False) -> dict:
    """Valida, construye, resuelve e interpreta.  Nunca lanza excepciones por datos malos."""
    errores = validar_escenario(escenario)
    if errores:
        return {"estado": "Datos invalidos", "errores": errores}
    prob, ctx = construir_modelo(escenario)
    if exportar_lp:
        prob.writeLP(exportar_lp)
    info = resolver(prob, tiempo_limite, gap_rel, mensajes_solver)
    if info["estado"] not in ("Optimal",):
        # Infeasible (p. ej. cobertura minima inalcanzable), Not Solved, etc.
        info["errores"] = []
        if info["estado"] == "Infeasible":
            info["errores"].append(
                "El modelo es infactible: probablemente las coberturas minimas exigidas "
                "no pueden satisfacerse con inventarios/rutas/capacidades disponibles.")
        return info
    return interpretar(ctx, info)


def cargar_json(ruta: str) -> dict:
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def imprimir_resumen(r: dict) -> None:
    if "errores" in r and r["errores"]:
        print("Estado:", r["estado"])
        for e in r["errores"]:
            print("  -", e)
        return
    print(f"Estado: {r['estado']} | objetivo = {r['valor_objetivo']:.4f} | "
          f"vars = {r['n_variables']} ({r['n_variables_enteras']} enteras) | "
          f"restr = {r['n_restricciones']} | t = {r['tiempo_s']:.3f}s")
    print(f"Cobertura global = {r['cobertura_global_pct']:.2f}% | ponderada = "
          f"{(r['cobertura_ponderada_pct'] or 0):.2f}% | costo = {r['costo_total']:.2f}")
    print("Cobertura por zona:", {z: None if p is None else round(p, 1)
                                  for z, p in r["cobertura_por_zona_pct"].items()})
    print("Cobertura por tipo:", {k: None if p is None else round(p, 1)
                                  for k, p in r["cobertura_por_tipo_pct"].items()})
    print("Envios (centro, zona, tipo): cantidad")
    for a, q in sorted(r["envios"].items()):
        print("  ", a, q)


if __name__ == "__main__":
    import sys
    esc = cargar_json(sys.argv[1])
    imprimir_resumen(optimizar(esc))
