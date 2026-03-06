import logging
import re
from pathlib import Path
from typing import List, Optional, Tuple

import ibis
import yaml

# --- GLOBAL CONFIGURATION ---
TYPE_GROUPS = {
    "string": ["string", "str", "varchar", "text", "String"],
    "int": ["int", "int32", "int64", "integer", "bigint", "Int64", "Int32"],
    "float": ["float", "float32", "float64", "double", "decimal", "Float64", "Decimal"],
    "bool": ["bool", "boolean", "Boolean"],
    "date": ["date", "Date"],
    "timestamp": ["timestamp", "datetime", "Timestamp"],
}


# --- AUXILIARY FUNCTIONS ---
def types_compatible(expected: str, actual: str) -> bool:
    """This function checks if two types are compatible based on logical groups,
    allowing for some flexibility in type naming conventions.
    Example: 'string' and 'varchar' would be considered compatible.

    Args:
        expected (str): The expected type as defined in the contract.
        actual (str): The actual type obtained from the database schema.

    Returns:
        bool: True if the types are considered compatible, False otherwise."""

    # Normalize to lowercase for comparison
    expected_l, actual_l = expected.lower(), actual.lower()

    # Check if both types belong to the same group
    for group in TYPE_GROUPS.values():
        if any(t.lower() in expected_l for t in group) and any(
            t.lower() in actual_l for t in group
        ):
            return True
    return expected_l == actual_l


def get_last_row_count(log_file: Path) -> Optional[int]:
    """This function reads the log file to find the last recorded row count for
    a table. It looks for lines that indicate the number of rows processed and extracts
    the most recent count. If the log file does not exist or if there is an error
    during reading, it returns None.

    Args:
        log_file (Path): The path to the log file for a specific table.

    Returns:
        Optional[int]: The last recorded row count if found, or None if not available."""

    # Check if the log file exists
    if not log_file.exists():
        return None

    # Regular expression to match lines like "100 rows" or "Actual 100"
    pattern = re.compile(r"(\d+)\srows|Actual\s(\d+)")
    last_count = (
        None  # Initialize last_count to None to handle cases where no matches are found
    )
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                matches = pattern.findall(line)
                for match in matches:
                    val = match[0] if match[0] else match[1]
                    last_count = int(val)
    except Exception:  # If there's an error reading the file, we simply return None
        return None
    return last_count


def setup_table_logger(
    table_name: str, log_dir: Path
) -> Tuple[logging.Logger, logging.FileHandler, Path]:
    """This function sets up a logger for a specific table. It creates a log file named after the table
    in the specified log directory. The logger is configured to write INFO level messages to the file,
    and it uses a standard format for log entries. If the logger already has handlers, they are cleared
    to avoid duplicate logging.

    Args:
        table_name (str): The name of the table for which the logger is being set up.
        log_dir (Path): The directory where the log file will be created.

    Returns:
        Tuple[logging.Logger, logging.FileHandler, Path]: A tuple containing the configured logger,
        the file handler, and the path to the log file."""

    # Set up logger for the specific table
    log_file = log_dir / f"{table_name}.log"
    logger = logging.getLogger(table_name)
    logger.setLevel(logging.INFO)

    # Clear existing handlers to avoid duplicate logs if the function is called multiple times.
    if logger.hasHandlers():
        logger.handlers.clear()

    # Create file handler for the table log and set formatter
    handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger, handler, log_file


def print_terminal_report(
    tablename: str,
    r_stat: str,
    r_act: int,
    r_exp: int,
    r_diff: str,
    s_ok: bool,
    miss: List[str],
    extra: List[str],
    mism: List[str],
) -> None:
    """This function prints a summary report to the terminal for a specific table after validation.
    It displays the table name, the status of row count validation, the actual and expected row counts,
    the difference from the previous count, and the results of schema validation. The report uses
    icons to indicate success or warnings, and it provides details about any missing columns, extra
    columns, or type mismatches in the schema.

    Args:
        tablename (str): The name of the table being reported on.
        r_stat (str): The status of row count validation ("OK" or "MISMATCH").
        r_act (int): The actual row count obtained from the database.
        r_exp (int): The expected row count defined in the contract.
        r_diff (str): A string indicating the difference from the previous row count.
        s_ok (bool): A boolean indicating whether the schema validation passed.
        miss (List[str]): A list of missing columns in the actual schema compared to the contract.
        extra (List[str]): A list of extra columns in the actual schema that are not defined in the contract.
        mism (List[str]): A list of type mismatches between the actual schema and the expected schema defined in the contract.

    Returns:
        None: This function does not return any value; it only prints the report to the terminal.
    """

    icon = "✅" if (r_stat == "OK" and s_ok) else "⚠️"
    print(f"\n{icon} TABLE: {tablename}")
    print(f"   Rows: {r_stat} ({r_act}/{r_exp}) {r_diff}")
    if s_ok:
        print(f"   Schema: ✅ OK")
    else:
        print(f"   Schema: ❌ ERROR")
        if miss:
            print(f"     - Missing: {miss}")
        if extra:
            print(f"     - Extra: {extra}")
        if mism:
            print(f"     - Types: {mism}")


# --- CORE VALIDATION FUNCTIONS ---


def validate_table(
    client: ibis.BaseBackend,
    table_name: str,
    database: str,
    contract_path: Path,
    log_dir: Path,
    strict_types: bool = False,
) -> bool:
    """This function performs a comprehensive validation for a specific table. It checks both
    the row count and the schema against the defined contract. The function logs the results of
    each validation step and prints a summary report to the terminal. If any critical error
    occurs during the process, it logs the error and returns False. Otherwise, it returns True
    if both row count and schema validations pass.

    Args:
        client (ibis.BaseBackend): The Ibis backend instance.
        table_name (str): The name of the table to validate.
        database (str): The name of the database containing the table.
        contract_path (Path): The path to the YAML contract file.
        log_dir (Path): The directory where log files will be stored.
        strict_types (bool): Whether to perform strict type checking.

    Returns:
        bool: True if the table passes validation, False otherwise.

    Raises:
        Exception: If there is a critical error during the validation process, an exception is raised and logged.
    """

    # Set up logger for this table
    logger, handler, log_path = setup_table_logger(table_name, log_dir)

    try:
        # Load contract YAML
        if not contract_path.exists():
            print(f"  ⚠️  Contract not found at: {contract_path}")
            return False

        with open(contract_path, "r") as f:
            contract = yaml.safe_load(f)

        # Extract actual schema and row count from the database
        ibis_table = client.table(table_name, database=database)
        actual_rows = ibis_table.count().execute()
        actual_schema = {col: str(typ) for col, typ in ibis_table.schema().items()}

        # Row count validation
        expected_rows = contract.get("expected_rows")
        prev_rows = get_last_row_count(log_path)

        row_status = "OK" if actual_rows == expected_rows else "MISMATCH"
        diff_info = (
            f"(Diff vs previous: {actual_rows - prev_rows:+})"
            if prev_rows is not None
            else "(First load)"
        )

        logger.info(
            f"ROWS {row_status}: Actual {actual_rows}, Expected {expected_rows} {diff_info}"
        )

        # Schema validation
        contract_cols = contract.get("schema", {}).get("columns", {})
        expected_schema = {
            k: v.get("type", "unknown")
            for k, v in contract_cols.items()  # If type is missing in contract, we mark it as 'unknown' to handle it gracefully
        }

        missing = [
            c for c in expected_schema if c not in actual_schema
        ]  # Columns defined in contract but missing in actual schema
        extra = [
            c for c in actual_schema if c not in expected_schema
        ]  # Columns present in actual schema but not defined in contract
        mismatches = []  # Initially empty list to store type mismatches

        for col, exp_type in expected_schema.items():
            if col in actual_schema:
                act_type = actual_schema[col]
                is_valid = (
                    (exp_type == act_type)
                    if strict_types
                    else types_compatible(
                        exp_type, act_type
                    )  # Check compatibility based on logical groups rather than exact match
                )
                if not is_valid:
                    mismatches.append(
                        f"{col}: {act_type} (expected {exp_type})"
                    )  # If there's a type mismatch, we add a descriptive message to the mismatches list

        schema_ok = not (missing or extra or mismatches)
        if (
            schema_ok
        ):  # If there are no missing columns, no extra columns, and no type mismatches, we log that the schema is OK
            logger.info("SCHEMA OK: All columns and types match.")
        else:  # If there are any issues with the schema, we log a warning with details about missing columns, extra columns, and type mismatches
            logger.warning(
                f"SCHEMA ERROR: Missing: {missing} | Extra: {extra} | Types: {mismatches}"
            )

        # Print terminal report with all the details
        print_terminal_report(
            table_name,
            row_status,
            actual_rows,
            expected_rows,
            diff_info,
            schema_ok,
            missing,
            extra,
            mismatches,
        )

        return row_status == "OK" and schema_ok

    # Throw an exception if there's a critical error during the validation process.
    except Exception as e:
        logger.error(f"FATAL ERROR in '{table_name}': {str(e)}")
        print(f"  ❌ Critical failure in '{table_name}': {e}")
        return False
    # Ensure that the file handler is properly closed and removed from the logger to prevent resource leaks and duplicate logging in future runs.
    finally:
        handler.close()
        logger.removeHandler(handler)


def run_global_audit(
    client: ibis.BaseBackend, tables: List[str], db_name: str, c_dir: Path, l_dir: Path
) -> None:
    """This function orchestrates the global audit process for multiple tables. It
    iterates through a list of table names, validates each table using the `validate_table`
    function, and keeps track of the results. The function also ensures that the log
    directory exists before starting the audit. At the end of the process, it prints
    a summary report indicating how many tables passed validation out of the total
    number of tables audited.

    Args:
        client (ibis.BaseBackend): The Ibis backend instance.
        tables (List[str]): A list of table names to be audited.
        db_name (str): The name of the database containing the tables.
        c_dir (Path): The directory where contract YAML files are stored.
        l_dir (Path): The directory where log files will be stored.

    Returns:
        None: This function does not return any value; it only performs the audit and prints the results to the terminal.
    """
    print(f"--- STARTING AUDIT ON DB:{db_name} ---")
    l_dir.mkdir(parents=True, exist_ok=True)

    results = {"total": len(tables), "passed": 0}

    for table in tables:
        yaml_file = c_dir / f"{table}.yaml"
        success = validate_table(client, table, db_name, yaml_file, l_dir)
        if success:
            results["passed"] += 1

    print(f"\n{'='*40}")
    print(f"SUMMARY: {results['passed']}/{results['total']} tables passed.")
    print(f"{'='*40}")