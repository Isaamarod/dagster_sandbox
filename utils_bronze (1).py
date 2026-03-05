#std
import yaml
from pathlib import Path
from typing import Dict, Any, List
#third party
import ibis

def _types_compatible(expected: str, actual: str) -> bool:
    """Verifica si dos tipos son compatibles (versión normalizada)."""
    type_groups = {
        "string": ["string", "str", "varchar", "text", "String"],
        "int": ["int", "int32", "int64", "integer", "bigint", "Int64", "Int32"],
        "float": ["float", "float32", "float64", "double", "decimal", "Float64", "Decimal"],
        "bool": ["bool", "boolean", "Boolean"],
        "date": ["date", "Date"],
        "timestamp": ["timestamp", "datetime", "Timestamp"],
    }
    expected_lower = expected.lower()
    actual_lower = actual.lower()

    for group, types in type_groups.items():
        expected_in_group = any(t.lower() in expected_lower for t in types)
        actual_in_group = any(t.lower() in actual_lower for t in types)
        if expected_in_group and actual_in_group:
            return True
    return expected_lower == actual_lower

def print_validation_report(result: Dict[str, Any]) -> None:
    """Imprime el reporte detallado que ya tenías."""
    print("=" * 60)
    print(f"📊 REPORTE DE VALIDACIÓN: {result.get('table', 'N/A').upper()}")
    print("=" * 60)
    if result["passed"]:
        print("✅ VALIDACIÓN EXITOSA - El esquema coincide con el contrato\n")
    else:
        print("❌ VALIDACIÓN FALLIDA - Se encontraron diferencias\n")

    print(f"Columnas esperadas: {result['total_columns_expected']}")
    print(f"Columnas actuales: {result['total_columns_actual']}\n")

    if result.get("missing_columns"):
        print("🚫 Columnas faltantes:")
        for col in result["missing_columns"]: print(f"  - {col}")
        print()
    if result.get("extra_columns"):
        print("➕ Columnas extra (no en contrato):")
        for col in result["extra_columns"]: print(f"  - {col}")
        print()
    if result.get("mismatches"):
        print("⚠️  Tipos incompatibles:")
        for m in result["mismatches"]:
            print(f"  - {m['column']}: Exp: {m['expected']} | Act: {m['actual']}")
        print()
    print("=" * 60)

def validate_multiple_ibis_tables(
    client: ibis.BaseBackend,
    tables_list: List[str],
    database_name: str,
    contracts_dir: Path,
    strict_types: bool = False
) -> Dict[str, Any]:
    """
    Orquestador que usa tu lógica original para validar una lista de tablas.
    """
    print(f"\n🚀 INICIANDO AUDITORÍA GLOBAL EN: {database_name} WEEE")
    
    global_summary = {"total": len(tables_list), "passed": 0, "failed": 0}
    
    for table_name in tables_list:
        # 1. Definir ruta del YAML basada en el nombre de la tabla
        yaml_path = contracts_dir / f"{table_name}.yaml"
        
        try:
            # 2. Obtener tabla del cliente Ibis
            ibis_table = client.table(table_name, database=database_name)
            
            # 3. Ejecutar TU lógica original de validación
            # (Integrada aquí para que use el yaml_path dinámico)
            with open(yaml_path, 'r') as file:
                contract = yaml.safe_load(file)
            
            ibis_schema = ibis_table.schema()
            actual_schema = {col: str(typ) for col, typ in ibis_schema.items()}
            
            expected_schema = {}
            if "schema" in contract and "columns" in contract["schema"]:
                for col, info in contract["schema"]["columns"].items():
                    expected_schema[col] = info.get("type", "unknown")
            
            mismatches = []
            missing_columns = [c for c in expected_schema if c not in actual_schema]
            extra_columns = [c for c in actual_schema if c not in expected_schema]

            for col, exp_type in expected_schema.items():
                if col in actual_schema:
                    act_type = actual_schema[col]
                    if strict_types:
                        if exp_type != act_type:
                            mismatches.append({"column": col, "expected": exp_type, "actual": act_type})
                    else:
                        if not _types_compatible(exp_type, act_type):
                            mismatches.append({"column": col, "expected": exp_type, "actual": act_type})

            result = {
                "passed": not (mismatches or missing_columns or extra_columns),
                "table": table_name,
                "expected_schema": expected_schema,
                "actual_schema": actual_schema,
                "mismatches": mismatches,
                "missing_columns": missing_columns,
                "extra_columns": extra_columns,
                "total_columns_expected": len(expected_schema),
                "total_columns_actual": len(actual_schema)
            }

            # 4. Imprimir reporte y actualizar contadores
            print_validation_report(result)
            if result["passed"]:
                global_summary["passed"] += 1
            else:
                global_summary["failed"] += 1

        except Exception as e:
            print(f"❌ ERROR CRÍTICO en tabla '{table_name}': {e}")
            global_summary["failed"] += 1

    print(f"\n✅ AUDITORÍA FINALIZADA: {global_summary['passed']} OK / {global_summary['failed']} Error")
    return global_summary