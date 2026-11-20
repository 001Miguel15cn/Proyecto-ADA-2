\* Distribucion_Ayudas_Humanitarias *\
Maximize
Cobertura_ponderada_menos_costo: - 0.75 s_Z1_A - s_Z1_B
 - 0.666666666667 s_Z2_A - s_Z2_B
Subject To
Balance_Z1_A: s_Z1_A + x_C1_Z1_A = 4
Balance_Z1_B: s_Z1_B + x_C1_Z1_B = 3
Balance_Z2_A: s_Z2_A + x_C1_Z2_A = 3
Balance_Z2_B: s_Z2_B + x_C1_Z2_B = 2
Despacho_C1: 3 x_C1_Z1_A + 2 x_C1_Z1_B + 3 x_C1_Z2_A + 2 x_C1_Z2_B <= 17
Inventario_C1_A: x_C1_Z1_A + x_C1_Z2_A <= 7
Inventario_C1_B: x_C1_Z1_B + x_C1_Z2_B <= 5
Ruta_C1_Z1: 3 x_C1_Z1_A + 2 x_C1_Z1_B <= 20
Ruta_C1_Z2: 3 x_C1_Z2_A + 2 x_C1_Z2_B <= 20
Bounds
 0 <= s_Z1_A <= 4
 0 <= s_Z1_B <= 3
 0 <= s_Z2_A <= 3
 0 <= s_Z2_B <= 2
 0 <= x_C1_Z1_A
 0 <= x_C1_Z1_B
 0 <= x_C1_Z2_A
 0 <= x_C1_Z2_B
Generals
s_Z1_A
s_Z1_B
s_Z2_A
s_Z2_B
x_C1_Z1_A
x_C1_Z1_B
x_C1_Z2_A
x_C1_Z2_B
End
