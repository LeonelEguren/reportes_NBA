from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, create_engine, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from fastapi.middleware.cors import CORSMiddleware
import bcrypt
from pydantic import BaseModel, EmailStr, Field
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
import datetime

# ==========================================
# CONFIGURACIÓN DE CORREO (fastapi-mail)
# ==========================================
conf = ConnectionConfig(
    MAIL_USERNAME="tu_usuario_de_mailtrap",          # Ejemplo: "a1b2c3d4e5f6g7"
    MAIL_PASSWORD="tu_contraseña_de_mailtrap",       # Ejemplo: "h8i9j0k1l2m3n4"
    MAIL_FROM="tu_correo_de_remitente@ejemplo.com",
    MAIL_PORT=2525,                                  # Mailtrap suele usar 2525 o 587
    MAIL_SERVER="sandbox.smtp.mailtrap.io",
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)

# ==========================================
# CONFIGURACIÓN DE BASE DE DATOS (SQLite)
# ==========================================
SQLALCHEMY_DATABASE_URL = "sqlite:///./nba_users.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ==========================================
# MODELOS DE LA BASE DE DATOS (SQLAlchemy)
# ==========================================

class UserDB(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String)
    apellido = Column(String)
    correo = Column(String, unique=True, index=True)
    contrasena = Column(String)  # Almacena el HASH

class NBATeamStatsDB(Base):
    __tablename__ = "nba_team_stats"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    season = Column(Integer, nullable=False, index=True)  # Año de la temporada 
    team = Column(String, nullable=False, index=True)    # Nombre del equipo 
    g = Column(Integer, nullable=False)                 # Partidos jugados 
    pts = Column(Integer, nullable=False)               # Puntos totales anotados 
    opp_pts = Column(Integer, nullable=False)           # Puntos totales recibidos 
    fg = Column(Integer, nullable=False)                # Tiros de campo convertidos 
    fga = Column(Integer, nullable=False)               # Tiros de campo intentados 
    fg3 = Column(Integer, nullable=True)                # Triples convertidos 
    fg3a = Column(Integer, nullable=True)               # Triples intentados 
    ft = Column(Integer, nullable=False)                # Tiros libres convertidos 
    trb = Column(Integer, nullable=False)               # Rebotes totales 
    ast = Column(Integer, nullable=False)               # Asistencias 
    tov = Column(Integer, nullable=True)                # Pérdidas de balón 
    blk = Column(Integer, nullable=True)                # Bloqueos 
    stl = Column(Integer, nullable=True)                # Robos 

class NBAPlayerStatsDB(Base):
    __tablename__ = "nba_player_stats"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    season = Column(Integer, nullable=False, index=True)
    player = Column(String, nullable=False, index=True)
    team = Column(String, nullable=False, index=True)
    pos = Column(String, nullable=True)
    g = Column(Integer, nullable=False)
    pts = Column(Integer, nullable=False)
    trb = Column(Integer, nullable=False)
    ast = Column(Integer, nullable=False)
    fg = Column(Integer, nullable=False)
    fga = Column(Integer, nullable=False)
    ft = Column(Integer, nullable=False)
    fta = Column(Integer, nullable=False)

class PrediccionDB(Base):
    __tablename__ = "predicciones"
    id_prediccion = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    equipo_local = Column(String, nullable=False)
    equipo_visitante = Column(String, nullable=False)
    ganador_predicho = Column(String, nullable=False)
    fecha_simulacion = Column(DateTime, default=datetime.datetime.utcnow)

class HistorialDB(Base):
    __tablename__ = "historial"
    id_historial = Column(Integer, primary_key=True, index=True, autoincrement=True)
    accion = Column(String, nullable=False)
    descripcion = Column(String, nullable=False)
    fecha = Column(DateTime, default=datetime.datetime.utcnow)
    id_usuario = Column(Integer, ForeignKey("usuarios.id"), nullable=False)


# ==========================================
# ESQUEMAS DE VALIDACIÓN (Pydantic)
# ==========================================

class UserCreate(BaseModel):
    nombre: str
    apellido: str
    correo: EmailStr
    contrasena: str

class UserLogin(BaseModel):
    correo: EmailStr
    contrasena: str

class ProfileUpdate(BaseModel):
    nombre: str = None
    apellido: str = None
    correo: EmailStr = None

class PasswordUpdate(BaseModel):
    contrasena_actual: str
    nueva_contrasena: str

class PasswordRecoveryRequest(BaseModel):
    correo: EmailStr

class PrediccionRequest(BaseModel):
    id_usuario: int
    equipo_local: str
    equipo_visitante: str

class PrediccionHistorial(BaseModel):
    id_prediccion: int
    equipo_local: str
    equipo_visitante: str
    ganador_predicho: str
    fecha_simulacion: datetime.datetime


# ==========================================
# DEPENDENCIAS
# ==========================================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ==========================================
# APLICACIÓN Y ENDPOINTS
# ==========================================
app = FastAPI(title="NBA Predictor API")

# Habilitar CORS para conectar con el Live Server de Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Asegurar la creación de todas las tablas en la base de datos local al iniciar la app
Base.metadata.create_all(bind=engine)


# ENDPOINT DE CONSULTA DE EQUIPOS (DICCIONARIO ESTÁTICO)
@app.get("/equipos", status_code=200)
def obtener_equipos_disponibles(db: Session = Depends(get_db)):    
    equipos_db = db.query(NBATeamStatsDB.team).distinct().all()
    
    if not equipos_db:
        return {"status": "success", "total_equipos": 0, "equipos": []}

    # Extraer los códigos y ordenarlos alfabéticamente
    codigos_equipos = sorted([equipo[0] for equipo in equipos_db])

    # Devolver una lista simple de códigos
    return {"status": "success", "total_equipos": len(codigos_equipos), "equipos": codigos_equipos}


# RF-01: Creación de Cuenta (Hashear)
@app.post("/usuarios/registro", status_code=status.HTTP_201_CREATED)
async def registrar_usuario(
    user: UserCreate, 
    background_tasks: BackgroundTasks, 
    db: Session = Depends(get_db)
):
    db_user = db.query(UserDB).filter(UserDB.correo == user.correo).first()
    if db_user:
        raise HTTPException(status_code=400, detail="El correo ya está registrado")
    
    password_bytes = user.contrasena.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password_bytes, salt).decode('utf-8')
    
    nuevo_usuario = UserDB(
        nombre=user.nombre, 
        apellido=user.apellido, 
        correo=user.correo, 
        contrasena=hashed_password
    )
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)
    
    message = MessageSchema(
        subject="cuenta creada exitosamente",
        recipients=[user.correo],
        body="cuenta creada exitosamente",
        subtype=MessageType.plain
    )
    
    fm = FastMail(conf)
    print(f" [CORREO SIMULADO] Cuenta creada exitosamente. Mail encolado para: {user.correo}")
    return {"mensaje": "Usuario creado con éxito", "id": nuevo_usuario.id}


# RF-02: Autenticación (Verificar)
@app.post("/usuarios/login")
def login(user_login: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(UserDB).filter(UserDB.correo == user_login.correo).first()
    if not db_user:
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")
    
    password_bytes = user_login.contrasena.encode('utf-8')
    hashed_bytes = db_user.contrasena.encode('utf-8')
    
    if not bcrypt.checkpw(password_bytes, hashed_bytes):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")
    
    return {
        "mensaje": "Login exitoso", 
        "usuario": {"id": db_user.id, "nombre": db_user.nombre, "correo": db_user.correo}
    }


# RF-03: Gestión de Perfil
@app.put("/usuarios/{user_id}/perfil")
# En un sistema real, aquí se usaría un token para verificar que el usuario
# que hace la petición es el mismo que el del user_id.
def actualizar_perfil(user_id: int, perfil_update: ProfileUpdate, db: Session = Depends(get_db)):
    db_user = db.query(UserDB).filter(UserDB.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    if perfil_update.nombre: db_user.nombre = perfil_update.nombre
    if perfil_update.apellido: db_user.apellido = perfil_update.apellido
    
    if perfil_update.correo and perfil_update.correo != db_user.correo:
        email_exists = db.query(UserDB).filter(UserDB.correo == perfil_update.correo).first()
        if email_exists:
            raise HTTPException(status_code=400, detail="El nuevo correo ya está en uso")
        db_user.correo = perfil_update.correo

    db.commit()
    return {"mensaje": "Perfil actualizado correctamente"}


# RF-04: Cambio de Contraseña
@app.put("/usuarios/{user_id}/cambiar-contrasena")
# Al igual que en el perfil, se debería validar que el usuario autenticado
# coincide con el user_id que se intenta modificar.
def cambiar_contrasena(user_id: int, pass_update: PasswordUpdate, db: Session = Depends(get_db)):
    db_user = db.query(UserDB).filter(UserDB.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    current_bytes = pass_update.contrasena_actual.encode('utf-8')
    db_bytes = db_user.contrasena.encode('utf-8')
    if not bcrypt.checkpw(current_bytes, db_bytes):
        raise HTTPException(status_code=400, detail="La contraseña actual es incorrecta")
    
    new_bytes = pass_update.nueva_contrasena.encode('utf-8')
    salt = bcrypt.gensalt()
    db_user.contrasena = bcrypt.hashpw(new_bytes, salt).decode('utf-8')
    
    db.commit()
    print(f" [CORREO] Enviando aviso de cambio de contraseña a: {db_user.correo}")
    return {"mensaje": "Contraseña actualizada correctamente"}


# RF-05: Recuperación de Clave
@app.post("/usuarios/recuperar-contrasena")
def recuperar_contrasena(recovery: PasswordRecoveryRequest, db: Session = Depends(get_db)):
    db_user = db.query(UserDB).filter(UserDB.correo == recovery.correo).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="El correo no está registrado")
    
    print(f" [CORREO] Enviando enlace de restablecimiento a: {recovery.correo}")
    return {"mensaje": "Se ha enviado un correo para restablecer la contraseña"}


# ENDPOINT DE SIMULACIÓN Y PREDICCIONES
@app.post("/predicciones/simular", status_code=200)
def simular_y_guardar_prediccion(req: PrediccionRequest, db: Session = Depends(get_db)):
    usuario = db.query(UserDB).filter(UserDB.id == req.id_usuario).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    ultima_temporada_local = db.query(func.max(NBATeamStatsDB.season)).filter(NBATeamStatsDB.team == req.equipo_local).scalar()
    ultima_temporada_visitante = db.query(func.max(NBATeamStatsDB.season)).filter(NBATeamStatsDB.team == req.equipo_visitante).scalar()

    if not ultima_temporada_local or not ultima_temporada_visitante:
        raise HTTPException(
            status_code=400, 
            detail=f"Faltan estadísticas en el dataset. Local encontrado: {bool(ultima_temporada_local)}, Visitante encontrado: {bool(ultima_temporada_visitante)}"
        )

    stats_local = db.query(NBATeamStatsDB).filter(NBATeamStatsDB.team == req.equipo_local, NBATeamStatsDB.season == ultima_temporada_local).first()
    stats_visitante = db.query(NBATeamStatsDB).filter(NBATeamStatsDB.team == req.equipo_visitante, NBATeamStatsDB.season == ultima_temporada_visitante).first()

    promedio_local = stats_local.pts / stats_local.g
    promedio_visitante = stats_visitante.pts / stats_visitante.g

    if promedio_local >= promedio_visitante:
        ganador = req.equipo_local
    else:
        ganador = req.equipo_visitante

    nueva_prediccion = PrediccionDB(
        id_usuario=req.id_usuario,
        equipo_local=req.equipo_local,
        equipo_visitante=req.equipo_visitante,
        ganador_predicho=ganador
    )
    db.add(nueva_prediccion)
    
    nuevo_historial = HistorialDB(
        accion="PREDICCIÓN RECIENTE",
        descripcion=f"Simuló {req.equipo_local} ({ultima_temporada_local}) vs {req.equipo_visitante} ({ultima_temporada_visitante}). Ganador predicho: {ganador}",
        id_usuario=req.id_usuario
    )
    db.add(nuevo_historial)
    
    db.commit()
    db.refresh(nueva_prediccion)

    return {
        "status": "success",
        "mensaje": "Predicción calculada y guardada con éxito",
        "resultado": {
            "id_prediccion": nueva_prediccion.id_prediccion,
            "id_usuario_vinculado": nueva_prediccion.id_usuario,
            "local": {
                "nombre": req.equipo_local,
                "ultima_temporada": ultima_temporada_local,
                "puntos_promedio": round(promedio_local, 2)
            },
            "visitante": {
                "nombre": req.equipo_visitante,
                "ultima_temporada": ultima_temporada_visitante,
                "puntos_promedio": round(promedio_visitante, 2)
            },
            "ganador_predicho": ganador
        }
    }

# RF-06: Endpoint para ver el historial de predicciones de un usuario
@app.get("/predicciones/usuario/{user_id}", status_code=200)
def obtener_historial_de_usuario(user_id: int, db: Session = Depends(get_db)):
    # Validar que el usuario exista
    usuario = db.query(UserDB).filter(UserDB.id == user_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # Obtener todas las predicciones para ese usuario, ordenadas por fecha descendente
    predicciones = db.query(PrediccionDB)\
        .filter(PrediccionDB.id_usuario == user_id)\
        .order_by(PrediccionDB.fecha_simulacion.desc())\
        .all()

    return {"status": "success", "predicciones": predicciones}
# ==========================================
# ENDPOINT DE JUGADORES
# ==========================================
@app.get("/jugadores/")
def listar_jugadores(temporada: int = None, db: Session = Depends(get_db)):
    # Si no se especifica temporada, usamos la más reciente disponible
    if temporada is None:
        temporada = db.query(func.max(NBAPlayerStatsDB.season)).scalar()

    jugadores = db.query(NBAPlayerStatsDB)\
        .filter(NBAPlayerStatsDB.season == temporada)\
        .all()

    resultado = []
    for j in jugadores:
        partidos = j.g if j.g > 0 else 1  # evita división por cero
        ppg = round(j.pts / partidos, 1)
        rpg = round(j.trb / partidos, 1)
        apg = round(j.ast / partidos, 1)
        ts_pct = round(
            j.pts / (2 * (j.fga + 0.44 * j.fta)), 3
        ) if (j.fga + j.fta) > 0 else 0.0

        resultado.append({
            "id": j.id,
            "name": j.player,
            "team": j.team,
            "pos": j.pos,
            "ppg": ppg,
            "rpg": rpg,
            "apg": apg,
            "per": 0,  # el dataset no trae PER calculado; lo dejamos en 0 por ahora
            "ts": ts_pct,
            "status": "ACTIVE"
        })

    return {
        "temporada": temporada,
        "total": len(resultado),
        "jugadores": resultado
    }