import csv
from main import SessionLocal, NBATeamStatsDB, NBAPlayerStatsDB, Base, engine

# Función auxiliar para convertir datos de forma segura
def limpiar_entero(valor):
    if not valor or valor == "NA" or valor == "NaN":
        return 0
    try:
        return int(valor)
    except ValueError:
        return 0

def importar_jugadores():
    archivo_path = "Team Totals.csv"
    print(" [SISTEMA] Leyendo estadísticas individuales de jugadores...")

    try:
        with SessionLocal() as db:
            jugadores_a_crear = []
            with open(archivo_path, mode="r", encoding="utf-8") as f:
                lector = csv.DictReader(f)

                for fila in lector:
                    if not fila.get("season") or not fila.get("team") or not fila.get("player"):
                        continue

                    team = fila["team"]
                    # Descartamos filas de jugadores transferidos (TOT)
                    if team == "TOT":
                        continue

                    jugador = NBAPlayerStatsDB(
                        season=int(fila["season"]),
                        player=fila["player"],
                        team=team,
                        pos=fila.get("pos") or None,
                        g=limpiar_entero(fila.get("g")),
                        pts=limpiar_entero(fila.get("pts")),
                        trb=limpiar_entero(fila.get("trb")),
                        ast=limpiar_entero(fila.get("ast")),
                        fg=limpiar_entero(fila.get("fg")),
                        fga=limpiar_entero(fila.get("fga")),
                        ft=limpiar_entero(fila.get("ft")),
                        fta=limpiar_entero(fila.get("fta"))
                    )
                    jugadores_a_crear.append(jugador)

            print(f" [SISTEMA] Migrando {len(jugadores_a_crear)} registros de jugadores a la base de datos...")
            db.bulk_save_objects(jugadores_a_crear)
            db.commit()
            print(f" [SISTEMA] ¡{len(jugadores_a_crear)} registros de jugadores cargados con éxito!")

    except FileNotFoundError:
        print(f" [ERROR] No se encontró el archivo '{archivo_path}'.")
    except Exception as e:
        db.rollback()
        print(f" [ERROR INESPERADO] {str(e)}")

def importar_y_consolidar_dataset():
    archivo_path = "Team Totals.csv" 
    
    print(" [SISTEMA] Leyendo estadísticas de jugadores y consolidando por equipo...")
    
    acumulador = {}
    
    try:
        with open(archivo_path, mode="r", encoding="utf-8") as f:
            lector = csv.DictReader(f)
            
            for fila in lector:
                # Validamos temporada y equipo básico
                if not fila.get("season") or not fila.get("team"):
                    continue
                    
                season = int(fila["season"])
                team = fila["team"]
                
                # Ignoramos los totales duplicados de jugadores traspasados
                if team == "TOT":
                    continue
                    
                clave = (season, team)
                
                if clave not in acumulador:
                    acumulador[clave] = {
                        "g": 0, "pts": 0, "fg": 0, "fga": 0,
                        "fg3": 0, "fg3a": 0, "ft": 0, "trb": 0, "ast": 0,
                        "tov": 0, "blk": 0, "stl": 0
                    }
                
                # Evaluamos los partidos jugados para estimar los del equipo
                partidos_jugador = limpiar_entero(fila.get("g"))
                if partidos_jugador > acumulador[clave]["g"]:
                    acumulador[clave]["g"] = partidos_jugador
                
                # Sumamos el resto de las métricas usando la limpieza de "NA"
                acumulador[clave]["pts"] += limpiar_entero(fila.get("pts"))
                acumulador[clave]["fg"] += limpiar_entero(fila.get("fg"))
                acumulador[clave]["fga"] += limpiar_entero(fila.get("fga"))
                acumulador[clave]["fg3"] += limpiar_entero(fila.get("x3p"))
                acumulador[clave]["fg3a"] += limpiar_entero(fila.get("x3pa"))
                acumulador[clave]["ft"] += limpiar_entero(fila.get("ft"))
                acumulador[clave]["trb"] += limpiar_entero(fila.get("trb"))
                acumulador[clave]["ast"] += limpiar_entero(fila.get("ast"))
                acumulador[clave]["tov"] += limpiar_entero(fila.get("tov"))
                acumulador[clave]["blk"] += limpiar_entero(fila.get("blk"))
                acumulador[clave]["stl"] += limpiar_entero(fila.get("stl"))

        with SessionLocal() as db:
            print(f" [SISTEMA] Migrando {len(acumulador)} registros consolidados a la base de datos...")
            
            # Guardamos la consolidación en la tabla de SQLite
            for (season, team), metrics in acumulador.items():
                stat = NBATeamStatsDB(
                    season=season,
                    team=team,
                    g=metrics["g"] if metrics["g"] > 0 else 82,
                    pts=metrics["pts"],
                    opp_pts=0, 
                    fg=metrics["fg"],
                    fga=metrics["fga"],
                    fg3=metrics["fg3"],
                    fg3a=metrics["fg3a"],
                    ft=metrics["ft"],
                    trb=metrics["trb"],
                    ast=metrics["ast"],
                    tov=metrics["tov"],
                    blk=metrics["blk"],
                    stl=metrics["stl"]
                )
                db.add(stat)
                
            db.commit()
            print(" [SISTEMA] ¡Dataset consolidado y cargado con éxito en nba_users.db!")
        
    except FileNotFoundError:
        print(f" [ERROR] No se encontró el archivo '{archivo_path}'.")
    except Exception as e:
        print(f" [ERROR INESPERADO] {str(e)}")

def inicializar_base_de_datos():
    print(" [SISTEMA] Creando todas las tablas en la base de datos si no existen...")
    # Crea las tablas (usuarios, predicciones, historial, etc.) definidas en main.py
    Base.metadata.create_all(bind=engine)
    print(" [SISTEMA] Tablas verificadas/creadas con éxito.")
    
    importar_y_consolidar_dataset()
    importar_jugadores()

if __name__ == "__main__":
    inicializar_base_de_datos()