"""
Sistema RAG (Retrieval Augmented Generation) para búsqueda en pólizas
"""

from typing import List, Dict, Any, Optional
import json
import re

class PolicyRAG:
    """Sistema simple de búsqueda semántica en pólizas"""
    
    def __init__(self):
        # En producción usaríamos ChromaDB con embeddings
        # Por ahora, implementamos búsqueda por keywords
        pass
    
    def search_coverage(
        self,
        policy_data: Dict[str, Any],
        surgery_type: str,
        patient_age: int
    ) -> Dict[str, Any]:
        """
        Busca si una cirugía está cubierta en la póliza
        
        Args:
            policy_data: Datos de la póliza
            surgery_type: Tipo de cirugía
            patient_age: Edad del paciente
            
        Returns:
            Información de cobertura encontrada
        """
        
        coberturas = policy_data.get("coberturas", {})
        exclusiones = policy_data.get("exclusiones", [])
        tipo_plan = policy_data.get("tipo_plan", "Básico")
        
        # Normalizar nombre de cirugía
        surgery_normalized = surgery_type.lower()
        
        result = {
            "cubierto": False,
            "porcentaje_cobertura": 0,
            "copago": 0,
            "limite_maximo": 0,
            "clausulas_aplicables": [],
            "restricciones": [],
            "notas": []
        }
        
        # Buscar en coberturas
        coverage_found = self._find_in_coverage(
            coberturas, 
            surgery_normalized, 
            tipo_plan
        )
        
        if coverage_found:
            result["cubierto"] = True
            result["porcentaje_cobertura"] = coverage_found.get("porcentaje", 80)
            result["copago"] = coverage_found.get("copago", 0)
            result["limite_maximo"] = coverage_found.get("limite", 0)
            result["clausulas_aplicables"].append(coverage_found.get("clausula", "Cobertura general"))
        
        # Buscar exclusiones
        exclusion_found = self._find_exclusion(exclusiones, surgery_normalized, patient_age)
        
        if exclusion_found:
            result["cubierto"] = False
            result["restricciones"].append(exclusion_found)
        
        # Agregar notas según tipo de plan
        if tipo_plan == "VIP":
            result["notas"].append("Plan VIP: Cobertura completa sin copago")
            result["copago"] = 0
        elif tipo_plan == "Premium":
            result["notas"].append("Plan Premium: Cobertura extendida")
        
        return result
    
    def _find_in_coverage(
        self,
        coberturas: Dict[str, Any],
        surgery: str,
        plan_type: str
    ) -> Optional[Dict[str, Any]]:
        """Busca cobertura específica para una cirugía"""
        
        # Mapeo de cirugías a coberturas
        coverage_map = {
            "apendicectomía": "cirugias_urgencia",
            "apendicectomia": "cirugias_urgencia",
            "cesárea": "maternidad",
            "cesarea": "maternidad",
            "histerectomía": "cirugias_ginecologicas",
            "histerectomia": "cirugias_ginecologicas",
            "colecistectomía": "cirugias_digestivas",
            "colecistectomia": "cirugias_digestivas",
            "hernia": "cirugias_generales",
            "artroscopia": "traumatologia",
        }
        
        # Buscar categoría
        category = None
        for keyword, cat in coverage_map.items():
            if keyword in surgery:
                category = cat
                break
        
        if not category:
            category = "cirugias_generales"  # Categoría por defecto
        
        # Obtener datos de cobertura
        if category in coberturas:
            return coberturas[category]
        
        # Cobertura por defecto según plan
        default_coverage = {
            "VIP": {"porcentaje": 100, "copago": 0, "limite": 50000, "clausula": "Cobertura total - Plan VIP"},
            "Premium": {"porcentaje": 90, "copago": 10, "limite": 30000, "clausula": "Cobertura amplia - Plan Premium"},
            "Básico": {"porcentaje": 70, "copago": 30, "limite": 15000, "clausula": "Cobertura estándar - Plan Básico"}
        }
        
        return default_coverage.get(plan_type, default_coverage["Básico"])
    
    def _find_exclusion(
        self,
        exclusiones: List[str],
        surgery: str,
        patient_age: int
    ) -> Optional[str]:
        """Busca si hay exclusiones aplicables"""
        
        for exclusion in exclusiones:
            exclusion_lower = exclusion.lower()
            
            # Buscar keywords en exclusión
            if surgery in exclusion_lower:
                return exclusion
            
            # Exclusiones por edad
            if "menores de" in exclusion_lower:
                age_match = re.search(r'menores de (\d+)', exclusion_lower)
                if age_match:
                    age_limit = int(age_match.group(1))
                    if patient_age < age_limit:
                        return exclusion
            
            if "mayores de" in exclusion_lower:
                age_match = re.search(r'mayores de (\d+)', exclusion_lower)
                if age_match:
                    age_limit = int(age_match.group(1))
                    if patient_age > age_limit:
                        return exclusion
        
        return None
    
    def format_coverage_report(self, coverage: Dict[str, Any]) -> str:
        """Formatea un reporte de cobertura en texto"""
        
        if coverage["cubierto"]:
            report = f"""
✅ COBERTURA ENCONTRADA
• Porcentaje cubierto: {coverage['porcentaje_cobertura']}%
• Copago: ${coverage['copago']}
• Límite máximo: ${coverage['limite_maximo']}

Cláusulas aplicables:
{chr(10).join(f"  - {c}" for c in coverage['clausulas_aplicables'])}
"""
        else:
            report = f"""
❌ NO CUBIERTO

Razones:
{chr(10).join(f"  - {r}" for r in coverage['restricciones'])}
"""
        
        if coverage["notas"]:
            report += f"\nNotas adicionales:\n{chr(10).join(f'  - {n}' for n in coverage['notas'])}"
        
        return report

# Singleton
policy_rag = PolicyRAG()