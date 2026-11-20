"""pruebas.py - escenario conceptual + generador de instancias pequena/mediana/grande."""
from pathlib import Path
import random
import sys

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import optimizador as o


def generar(nC, nZ, nK, semilla=1, p_ruta=0.8, p_bloq=0.1, p_indiv=0.5):
    rnd = random.Random(semilla)
    K = [f"K{i+1}" for i in range(nK)]
    tipos = [{"id": k, "divisible": rnd.random() > p_indiv, "volumen": rnd.choice([1, 2, 3, 5]),
              "importancia": rnd.choice([1.0, 1.0, 1.5])} for k in K]
    zonas = [{"id": f"Z{i+1}", "poblacion": rnd.randint(200, 2000),
              "prioridad": rnd.choice(["Critica", "Alta", "Media", "Baja"]),
              "demanda": {k: rnd.randint(5, 60) for k in K}} for i in range(nZ)]
    dem_tot = {k: sum(z["demanda"][k] for z in zonas) for k in K}
    centros = [{"id": f"C{i+1}", "activo": True, "cap_despacho": rnd.randint(150, 500),
                "inventario": {k: int(dem_tot[k] * rnd.uniform(0.5, 0.9) / nC) for k in K}}
               for i in range(nC)]
    rutas = [{"origen": c["id"], "destino": z["id"], "disponible": rnd.random() > p_bloq,
              "costo": rnd.randint(1, 9), "capacidad": rnd.randint(60, 250)}
             for c in centros for z in zonas if rnd.random() < p_ruta]
    return {"tipos_ayuda": tipos, "prioridades": {"Critica": 4, "Alta": 3, "Media": 2, "Baja": 1},
            "centros": centros, "zonas": zonas, "rutas": rutas}


if __name__ == "__main__":
    print("=== Escenario conceptual ===")
    ruta_escenario = BASE_DIR / "escenario_conceptual.json"
    r = o.optimizar(o.cargar_json(ruta_escenario))
    o.imprimir_resumen(r)
    print("Inventario restante:", r["inventario_restante"])
    print("\n=== Instancias de prueba ===")
    print(f"{'Inst':<9}{'CxZxK':<9}{'vars':>6}{'enteras':>8}{'restr':>7}{'t(s)':>8}{'objetivo':>10}{'cob%':>7}{'no atend':>9}")
    for nombre, (c, z, k) in {"Pequena": (3, 5, 3), "Mediana": (5, 12, 5), "Grande": (10, 30, 8),
                              "Grande+": (15, 50, 10)}.items():
        esc = generar(c, z, k, semilla=7)
        r = o.optimizar(esc, tiempo_limite=60)
        if "cobertura_global_pct" not in r:
            print(nombre, r["estado"], r.get("errores")); continue
        na = sum(r["demanda_no_atendida"].values())
        print(f"{nombre:<9}{f'{c}x{z}x{k}':<9}{r['n_variables']:>6}{r['n_variables_enteras']:>8}"
              f"{r['n_restricciones']:>7}{r['tiempo_s']:>8.3f}{r['valor_objetivo']:>10.3f}"
              f"{r['cobertura_global_pct']:>7.1f}{na:>9.0f}")