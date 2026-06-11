from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import bcrypt
from pydantic import BaseModel, EmailStr
from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks
# ... tus otros imports de SQLAlchemy, Pydantic, bcrypt ...
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
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

# 1. Configuración de Base de Datos
SQLALCHEMY_DATABASE_URL = "sqlite:///./nba_users.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 2. Seguridad: Configuración de Hashing


# 3. Modelo de la Tabla (Base de Datos)
class UserDB(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String)
    apellido = Column(String)
    correo = Column(String, unique=True, index=True)
    contrasena = Column(String) # Almacena el HASH

Base.metadata.create_all(bind=engine)

# 4. Esquemas Pydantic (Validación de entrada/salida)
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

# 5. Dependencia para la DB
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 6. APP y Endpoints
app = FastAPI(title="NBA Predictor API")


# RF-01: Creación de Cuenta (Hashear)
@app.post("/usuarios/registro", status_code=status.HTTP_201_CREATED)
async def registrar_usuario(
    user: UserCreate, 
    background_tasks: BackgroundTasks, 
    db: Session = Depends(get_db)
):
    # 1. Validar si ya existe el correo
    db_user = db.query(UserDB).filter(UserDB.correo == user.correo).first()
    if db_user:
        raise HTTPException(status_code=400, detail="El correo ya está registrado")
    
    # 2. Hashear la contraseña con bcrypt puro
    password_bytes = user.contrasena.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password_bytes, salt).decode('utf-8')
    
    # 3. Guardar en la Base de Datos SQLite
    nuevo_usuario = UserDB(
        nombre=user.nombre, 
        apellido=user.apellido, 
        correo=user.correo, 
        contrasena=hashed_password
    )
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)
    
    # 4. Estructurar el Correo Simple (Asunto y Cuerpo igual a tu pedido)
    message = MessageSchema(
        subject="cuenta creada exitosamente",
        recipients=[user.correo],              # Le llega al correo ingresado en el JSON
        body="cuenta creada exitosamente",
        subtype=MessageType.plain              # Texto plano y simple sin HTML complejo
    )
    
    fm = FastMail(conf)
    
    # Con add_task, FastAPI responde de inmediato al navegador (21 Created) 
    # y se queda mandando el mail de fondo por atrás sin ralentizar la app.
    background_tasks.add_task(fm.send_message, message)
    
    print(f" [SISTEMA] Tarea de correo encolada para: {user.correo}")
    return {"mensaje": "Usuario creado con éxito", "id": nuevo_usuario.id}

# RF-02: Autenticación (Verificar)
@app.post("/usuarios/login")
def login(user_login: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(UserDB).filter(UserDB.correo == user_login.correo).first()
    if not db_user:
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")
    
    # Comparamos el texto plano entrante contra el hash de la base de datos
    password_bytes = user_login.contrasena.encode('utf-8')
    hashed_bytes = db_user.contrasena.encode('utf-8')
    
    if not bcrypt.checkpw(password_bytes, hashed_bytes):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")
    
    return {
        "mensaje": "Login exitoso", 
        "usuario": {"id": db_user.id, "nombre": db_user.nombre, "correo": db_user.correo}
    }


# RF-03: Gestión de Perfil (Sin tocar contraseña)
@app.put("/usuarios/{user_id}/perfil")
def actualizar_perfil(user_id: int, perfil_update: ProfileUpdate, db: Session = Depends(get_db)):
    db_user = db.query(UserDB).filter(UserDB.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    if perfil_update.nombre: db_user.nombre = perfil_update.nombre
    if perfil_update.apellido: db_user.apellido = perfil_update.apellido
    
    # Si cambia el correo, verificar que no esté duplicado
    if perfil_update.correo and perfil_update.correo != db_user.correo:
        email_exists = db.query(UserDB).filter(UserDB.correo == perfil_update.correo).first()
        if email_exists:
            raise HTTPException(status_code=400, detail="El nuevo correo ya está en uso")
        db_user.correo = perfil_update.correo

    db.commit()
    return {"mensaje": "Perfil actualizado correctamente"}


# RF-04: Cambio de Contraseña (Validar y Re-hashear)
@app.put("/usuarios/{user_id}/cambiar-contrasena")
def cambiar_contrasena(user_id: int, pass_update: PasswordUpdate, db: Session = Depends(get_db)):
    db_user = db.query(UserDB).filter(UserDB.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Validar contraseña actual
    current_bytes = pass_update.contrasena_actual.encode('utf-8')
    db_bytes = db_user.contrasena.encode('utf-8')
    if not bcrypt.checkpw(current_bytes, db_bytes):
        raise HTTPException(status_code=400, detail="La contraseña actual es incorrecta")
    
    # Hashear la nueva
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
    
    # Por seguridad en ambientes reales a veces se devuelve 200 aunque no exista, 
    # pero para desarrollo filtramos si existe o no.
    if not db_user:
        raise HTTPException(status_code=404, detail="El correo no está registrado")
    
    # Aquí generarías un token temporal de recuperación
    print(f" [CORREO] Enviando enlace de restablecimiento a: {recovery.correo}")
    return {"mensaje": "Se ha enviado un correo para restablecer la contraseña"}