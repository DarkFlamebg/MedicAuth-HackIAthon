import requests
import time

from app.core.config import settings

# 1. CONFIGURACIÓN DE CREDENCIALES
NOTION_TOKEN = settings.NOTION_TOKEN
PAGE_ID = settings.NOTION_PAGE_ID

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

url_databases = "https://api.notion.com/v1/databases"
# CREAR LA DATABASE 2 (PÓLIZAS DE SEGUROS)

print("Creando Database 2: Pólizas de Seguros...")

payload_polizas = {
    "parent": {"type": "page_id", "page_id": PAGE_ID},
    "title": [{"type": "text", "text": {"content": "Pólizas de Seguros"}}],
    "properties": {
        "Número Póliza": {"title": {}},  
        "Titular": {"rich_text": {}},
        "Coberturas": {"rich_text": {}},
        "Exclusiones": {"rich_text": {}},
        "Carencia Días": {"number": {"format": "number"}},
        "Fecha Inicio": {"date": {}},
        "Fecha Fin": {"date": {}},
        "Aseguradora": {
            "select": {
                "options": [{"name": "Seguros Sucre", "color": "blue"}]
            }
        },
        "Tipo Plan": {
            "select": {
                "options": [
                    {"name": "Básico", "color": "gray"},
                    {"name": "Premium", "color": "orange"},  
                    {"name": "VIP", "color": "purple"}
                ]
            }
        },
        "Estado": {
            "select": {
                "options": [
                    {"name": "Activa", "color": "green"},
                    {"name": "Suspendida", "color": "red"},
                    {"name": "Vencida", "color": "orange"}
                ]
            }
        },
        "Documento Póliza": {"files": {}}
    }
}

response_polizas = requests.post(url_databases, json=payload_polizas, headers=headers)

if response_polizas.status_code == 200:
    polizas_data = response_polizas.json()
    polizas_db_id = polizas_data["id"]
    print(f"-> ¡Database 'Pólizas de Seguros' creada con éxito! ID: {polizas_db_id}")
else:
    print(f"Error al crear Pólizas: {response_polizas.status_code}\n{response_polizas.text}")
    exit()
time.sleep(1)

# CREAR LA DATABASE 1 (SOLICITUDES DE AUTORIZACIÓN)
print("\nCreando Database 1: Solicitudes de Autorización...")

payload_solicitudes = {
    "parent": {"type": "page_id", "page_id": PAGE_ID},
    "title": [{"type": "text", "text": {"content": "Solicitudes de Autorización"}}],
    "properties": {
        "ID Solicitud": {"title": {}}, 
        "Paciente Nombre": {"rich_text": {}},
        "Cédula": {"rich_text": {}},
        "Médico Tratante": {"rich_text": {}},
        "Decisión IA": {"rich_text": {}},
        "Razonamiento": {"rich_text": {}},
        "Edad": {"number": {"format": "number"}},
        "Score Confianza": {"number": {"format": "number"}},
        "Tiempo Procesamiento": {"number": {"format": "number"}},
        "Fecha Solicitada": {"date": {}},
        "Fecha Respuesta": {"date": {}},
        "Informe Médico": {"files": {}},
        
        "Número Póliza": {
            "relation": {
                "database_id": polizas_db_id,
                "type": "single_property",
                "single_property": {}
            }
        },
        
        "Tipo Cirugía": {
            "select": {
                "options": [
                    {"name": "Apendicectomía", "color": "blue"},
                    {"name": "Cesárea", "color": "pink"}
                ]
            }
        },
        "Hospital": {
            "select": {
                "options": [
                    {"name": "Hospital Metropolitano", "color": "green"},
                    {"name": "Hospital Alcívar", "color": "orange"}
                ]
            }
        },
        "Estado": {
            "select": {
                "options": [
                    {"name": "Pendiente", "color": "yellow"},
                    {"name": "Aprobado", "color": "green"},
                    {"name": "Rechazado", "color": "red"},
                    {"name": "Docs Faltantes", "color": "orange"}
                ]
            }
        },
        "Documentos Faltantes": {
            "multi_select": {
                "options": [
                    {"name": "Cédula Identidad", "color": "red"},
                    {"name": "Historia Clínica", "color": "red"},
                    {"name": "Exámenes de Laboratorio", "color": "red"}
                ]
            }
        }
    }
}

response_solicitudes = requests.post(url_databases, json=payload_solicitudes, headers=headers)

if response_solicitudes.status_code == 200:
    solicitudes_data = response_solicitudes.json()
    print(f"-> ¡Database 'Solicitudes de Autorización' creada con éxito! ID: {solicitudes_data['id']}")
    print("\n¡ESTRUCTURA INTEGRAL COMPLETADA CON ÉXITO! Ve a mirar tu Notion.")
else:
    print(f"Error al crear Solicitudes: {response_solicitudes.status_code}\n{response_solicitudes.text}")