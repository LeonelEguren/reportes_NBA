# 🏀 NBA Predictor API - Módulo Backend (Fase de Prueba)

## 📝 Descripción del Proyecto
Este proyecto es un **Sistema de Análisis Predictivo de Rendimiento de Equipos de la NBA** diseñado para procesar datos históricos y simular enfrentamientos analíticos entre diferentes franquicias. 

Actualmente, el sistema se encuentra en su fase de desarrollo del backend. Cuenta con una arquitectura robusta basada en **FastAPI**, persistencia relacional con **SQLAlchemy (SQLite)** y validación de datos mediante **Pydantic**. 

El núcleo predictivo implementa una regla de negocio analítica avanzada: cuando se simula un partido, la API busca dinámicamente la **última formación disponible (la temporada más reciente)** de cada equipo en el dataset, calcula de forma independiente sus promedios reales de puntos por partido (`pts / g`) e identifica al ganador actual. Cada simulación queda registrada de forma permanente indexada al ID del usuario y deja una traza de auditoría en la tabla de historial.

---

## 🛠️ Instructivo Paso a Paso para Correr la Prueba

Seguí estos pasos en tu terminal para replicar el entorno, migrar los datos y ejecutar tus propias predicciones desde la documentación interactiva:

### 1. Preparar el Entorno Virtual e Instalar Dependencias
Abrí la consola dentro de la carpeta raíz del proyecto (`NBA/`) y ejecutá:
```bash
# 1. Crear el entorno virtual
python -m venv .venv

# 2. Activar el entorno virtual (En Windows / PowerShell)
.\.venv\Scripts\Activate.ps1

# 3. Instalar los paquetes necesarios
pip install fastapi uvicorn sqlalchemy bcrypt pydantic[email] fastapi-mail


2. Ubicar el Dataset de Kaggle
Asegurate de que el archivo CSV con las estadísticas esté guardado en la carpeta raíz del proyecto (al mismo nivel que main.py) y renombrado exactamente como: Team Totals.csv.

3. Ejecutar la Consolidación y Carga de Datos
Dado que el dataset original contiene registros individuales por jugador y valores nulos (NA), creamos un script que automatiza la limpieza y agrupa todo por franquicia en memoria antes de subirlo a SQLite. Corré el script con:

Bash
python cargar_dataset.py
Deberías ver en consola un mensaje indicando que se migraron con éxito los 1974 registros consolidados de la historia de la NBA.

4. Levantar el Servidor de la API
Iniciá el servidor local de desarrollo utilizando Uvicorn:

Bash
uvicorn main:app --reload
La consola te indicará que la aplicación ya está corriendo en: http://127.0.0.1:8000

5. Realizar la Prueba de Predicciones (Swagger)
Ingresá desde tu navegador web a la documentación interactiva: http://127.0.0.1:8000/docs

Registrar un usuario de prueba: Desplegá el endpoint POST /usuarios/registro, dale a Try it out y registrá un usuario cualquiera para generar un ID válido en el sistema (ej: id: 1).

Simular el partido: Desplegá el endpoint POST /predicciones/simular, presioná Try it out y pasale el JSON de entrada con el ID de tu usuario y las siglas oficiales en mayúscula de los equipos (por ejemplo, LAL para Los Angeles Lakers vs BOS para Boston Celtics):

JSON
{
  "id_usuario": 1,
  "equipo_local": "LAL",
  "equipo_visitante": "BOS"
}
Presioná el botón azul Execute. La API procesará la lógica analítica sobre la última temporada y te devolverá el ganador real guardando el resultado.

6. Auditar los Resultados Guardados en la DB
Para constatar de forma rápida que los datos se escribieron correctamente en las tablas de predicciones y de historial sin tener que abrir un gestor de base de datos externo, ejecutá nuestro script de consulta:

Bash
python ver_predicciones.py