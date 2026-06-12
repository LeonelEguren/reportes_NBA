import sqlite3

def consultar_tablas():
    # Conectar a tu base local
    conexion = sqlite3.connect("nba_users.db")
    cursor = conexion.cursor()

    # 1. Consultar Predicciones
    cursor.execute("SELECT id_prediccion, id_usuario, equipo_local, equipo_visitante, ganador_predicho FROM predicciones;")
    predicciones = cursor.fetchall()

    print("\n=======================================================")
    print("🔥 PREDICCIONES GUARDADAS EN LA BASE DE DATOS 🔥")
    print("=======================================================")
    if not predicciones:
        print("No hay predicciones registradas todavía.")
    for p in predicciones:
        print(f"ID Pred: {p[0]} | User ID: {p[1]} | {p[2]} vs {p[3]} ➔ GANADOR: {p[4]}")

    # 2. Consultar Historial
    cursor.execute("SELECT id_historial, accion, descripcion, id_usuario FROM historial;")
    historiales = cursor.fetchall()

    print("\n=======================================================")
    print("📋 HISTORIAL DE AUDITORÍA REGISTRADO 📋")
    print("=======================================================")
    if not historiales:
        print("No hay eventos en el historial todavía.")
    for h in historiales:
        print(f"ID Hist: {h[0]} | Acción: {h[1]} | User ID: {h[3]} | Detalles: {h[2]}")
    print("=======================================================\n")

    conexion.close()

if __name__ == "__main__":
    consultar_tablas()