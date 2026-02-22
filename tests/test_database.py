import pytest
from core.database import DatabaseManager

@pytest.fixture
def db():
    # Inicializa una base de datos en memoria para los tests
    manager = DatabaseManager(db_path=":memory:")
    return manager

def test_init_db(db):
    # Ya se llamó en el __init__
    with db._connect() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT count(name) FROM sqlite_master WHERE type='table' AND name='historial'")
        assert cursor.fetchone()[0] == 1

def test_guardar_y_obtener_historial(db):
    db.guardar_mensaje(1, "user", "Hola")
    db.guardar_mensaje(1, "assistant", "¡Hola! ¿En qué puedo ayudarte?")
    
    historial = db.obtener_historial(1)
    assert len(historial) == 2
    assert historial[0]["role"] == "user"
    assert historial[0]["content"] == "Hola"
    assert historial[1]["role"] == "assistant"
    assert historial[1]["content"] == "¡Hola! ¿En qué puedo ayudarte?"

def test_obtener_historial_alternancia(db):
    db.guardar_mensaje(1, "user", "Hola")
    db.guardar_mensaje(1, "user", "Hola de nuevo") # No debería aparecer seguido
    db.guardar_mensaje(1, "assistant", "¡Hola!")
    
    historial = db.obtener_historial(1)
    
    # "Hola de nuevo", seguido de assistant "¡Hola!" 
    assert len(historial) == 2
    assert historial[-1]["role"] == "assistant"
    assert historial[0]["role"] == "user"
    assert historial[0]["content"] == "Hola de nuevo"

def test_contar_mensajes(db):
    db.guardar_mensaje(1, "user", "Mensaje 1")
    db.guardar_mensaje(1, "user", "Mensaje 2")
    db.guardar_mensaje(1, "assistant", "Respuesta")
    assert db.contar_mensajes(1, "user") == 2
    assert db.contar_mensajes(1, "assistant") == 1

def test_borrar_historial(db):
    db.guardar_mensaje(2, "user", "Test")
    db.borrar_historial(2)
    assert len(db.obtener_historial(2)) == 0

def test_obtener_actualizar_perfil(db):
    db.actualizar_perfil(1, "Le gusta el café")
    assert db.obtener_perfil(1) == "Le gusta el café"
    
    db.actualizar_perfil(1, "Le gusta el café y el té")
    assert db.obtener_perfil(1) == "Le gusta el café y el té"

def test_obtener_o_crear_humor(db):
    humor = db.obtener_o_crear_humor(3)
    assert humor is not None
    assert type(humor) is str
    
    # Debería devolver el mismo
    assert db.obtener_o_crear_humor(3) == humor

def test_actualizar_humor(db):
    db.actualizar_humor(4, "feliz")
    assert db.obtener_o_crear_humor(4) == "feliz"

def test_guardar_obtener_borrar_nota(db):
    id_nota = db.guardar_nota(1, "Comprar pan")
    notas = db.obtener_notas(1)
    
    assert len(notas) == 1
    assert notas[0]["contenido"] == "Comprar pan"
    assert notas[0]["id"] == id_nota
    
    borrado = db.borrar_nota(1, id_nota)
    assert borrado is True
    assert len(db.obtener_notas(1)) == 0

def test_guardar_obtener_borrar_recordatorio(db):
    id_rec = db.guardar_recordatorio(1, 100, "Avisar algo", "2030-01-01 10:00:00")
    
    pendientes = db.obtener_recordatorios_pendientes()
    assert len(pendientes) == 1
    assert pendientes[0]["mensaje"] == "Avisar algo"
    
    borrado = db.borrar_recordatorio(id_rec)
    assert borrado is True
    assert len(db.obtener_recordatorios_pendientes()) == 0
