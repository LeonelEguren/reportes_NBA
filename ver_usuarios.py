import sqlite3

# Conectar a la base de datos local
conexion = sqlite3.connect("nba_users.db")
cursor = conexion.cursor()

# Ejecutar la consulta SQL
cursor.execute("SELECT id, nombre, apellido, correo, contrasena FROM usuarios;")
usuarios = cursor.fetchall()

print("\n--- USUARIOS REGISTRADOS EN LA BASE DE DATOS ---")
for u in usuarios:
    print(f"ID: {u[0]} | Nombre: {u[1]} {u[2]} | Correo: {u[3]} | Hash Clave: {u[4][:20]}...")
print("------------------------------------------------\n")

conexion.close()