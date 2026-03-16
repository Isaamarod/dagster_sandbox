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
def types_compatible(expected: str, current: str) -> bool:
    """This function checks if two types are compatible based on logical groups,
    allowing for some flexibility in type naming conventions.
    Example: 'string' and 'varchar' would be considered compatible.

    Args:
        expected (str): The expected type as defined in the contract.
        current (str): The current type obtained from the database schema.

    Returns:
        bool: True if the types are considered compatible, False otherwise."""

    # Normalize to lowercase for comparison
    expected_l, current_l = expected.lower(), current.lower()

    # Check if both types belong to the same group
    for group in TYPE_GROUPS.values():
        if any(t.lower() in expected_l for t in group) and any(
            t.lower() in current_l for t in group
        ):
            return True
    return expected_l == current_l


def get_last_stats(log_file: Path) -> Tuple[Optional[int], Optional[int]]:
    """This function reads the log file to find the last recorded row count and variable count for
    a table. It looks for lines that indicate the number of rows and variables processed and extracts
    the most recent counts. If the log file does not exist or if there is an error during reading,
    it returns None for both counts.

    Args:
        log_file (Path): The path to the log file for a specific table.

    Returns:
        Tuple[Optional[int], Optional[int]]: A tuple containing the last recorded row count and
        variable count if found, or None for each if not available.

    Raises:
        Exception: If there is an error during file reading, the function will return None for
        both counts without raising an exception, allowing the calling code to handle the absence
        of data gracefully.
    """

    # Check if the log file exists
    if not log_file.exists():
        return None, None

    # Regular expression to match lines like "ROWS ... Current 100" and "VARS ... Current 5"
    row_pattern = re.compile(r"ROWS .*? Current (\d+)")
    var_pattern = re.compile(r"VARS .*? Current (\d+)")

    last_row, last_var = (
        None,
        None,
    )  # Initialize to None to handle cases where no matches are found

    try:
        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                # Get last row count
                row_match = row_pattern.search(line)
                if row_match:
                    last_row = int(row_match.group(1))

                # Get last variable count
                var_match = var_pattern.search(line)
                if var_match:
                    last_var = int(var_match.group(1))

    except (
        Exception
    ):  # If there's an error reading the file, we simply return None for both
        return None, None

    return last_row, last_var


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
    r_current: int,
    r_exp: int,
    r_diff: str,
    v_stat: str,
    v_current: int,
    v_exp: int,
    v_diff: str,
    s_ok: bool,
    miss: List[str],
    extra: List[str],
    mism: List[str],
) -> None:
    """This function prints a summary report to the terminal for a specific table after validation.
    It displays the table name, the status of row count validation, the current and expected row counts,
    the difference from the previous count, and the results of schema validation. The report uses
    icons to indicate success or warnings, and it provides details about any missing columns, extra
    columns, or type mismatches in the schema.

    Args:
        tablename (str): The name of the table being reported on.
        r_stat (str): The status of row count validation ("OK" or "MISMATCH").
        r_current (int): The current row count obtained from the database.
        r_exp (int): The expected row count defined in the contract.
        r_diff (str): A string indicating the difference from the previous row count.
        v_stat (str): The status of variable count validation ("OK" or "MISMATCH").
        v_current (int): The current variable count obtained from the database.
        v_exp (int): The expected variable count defined in the contract.
        v_diff (str): A string indicating the difference from the previous variable count.
        s_ok (bool): A boolean indicating whether the schema validation passed.
        miss (List[str]): A list of missing columns in the current schema compared to the contract.
        extra (List[str]): A list of extra columns in the current schema that are not defined in the contract.
        mism (List[str]): A list of type mismatches between the current schema and the expected schema defined in the contract.

    Returns:
        None: This function does not return any value; it only prints the report to the terminal.
    """

    overall_ok = (
        r_stat == "OK" and v_stat == "OK" and s_ok
    )  # Overall status based on all validations
    icon = "✅" if overall_ok else "⚠️"

    print(f"\n{icon} TABLE: {tablename}")
    print(f"   Rows: {r_stat} (Current: {r_current}, Expected: {r_exp}) {r_diff}")
    print(f"   Variables: {v_stat} (Current: {v_current}, Expected: {v_exp}) {v_diff}")
    if s_ok:
        print(f"   Schema: ✅ OK")
    else:
        print(f"   Schema: ❌ ERROR")
        if miss:
            print(f"     - Missing: {miss}")
        if extra:
            print(f"     - Extra: {extra}")
        if mism:
            print(f"     - Type Mismatches: {mism}")


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

        # Extract current schema and row count from the database
        ibis_table = client.table(table_name, database=database)
        current_rows = ibis_table.count().execute()
        current_schema = {col: str(typ) for col, typ in ibis_table.schema().items()}
        current_vars = len(current_schema)

        # Row count validation
        prev_rows, prev_vars = get_last_stats(log_path)
        expected_rows = contract.get("expected_rows", 0)
        contract_cols = contract.get("schema", {}).get("columns", {})
        expected_vars = len(contract_cols)

        # Row validation logic
        row_status = "OK" if current_rows == expected_rows else "MISMATCH"
        row_diff_info = (
            f"(Diff vs previous: {current_rows - prev_rows:+})"
            if prev_rows is not None
            else "(First load)"
        )

        # Variable validation logic (column count)
        var_status = "OK" if current_vars == expected_vars else "MISMATCH"
        var_diff_info = (
            f"(Diff vs previous: {current_vars - prev_vars:+})"
            if prev_vars is not None
            else "(First load)"
        )

        logger.info("="*80) # Log separator for better readability between runs
        logger.info(
            f"ROWS {row_status}: Current {current_rows}, Expected {expected_rows} {row_diff_info}"
        )
        logger.info(
            f"VARS {var_status}: Current {current_vars}, Expected {expected_vars} {var_diff_info}"
        )

        # Detailed schema validation
        expected_schema = {
            k: v.get("type", "unknown") for k, v in contract_cols.items()
        }  # If type is missing in contract, we mark it as 'unknown' to handle it gracefully

        missing = [
            c for c in expected_schema if c not in current_schema
        ]  # Columns defined in contract but missing in current schema
        extra = [
            c for c in current_schema if c not in expected_schema
        ]  # Columns present in current schema but not defined in contract

        mismatches = []  # Initially empty list to store type mismatches

        for col, exp_type in expected_schema.items():
            if col in current_schema:
                current_type = current_schema[col]
                is_valid = (
                    (exp_type == current_type)
                    if strict_types
                    else types_compatible(
                        exp_type, current_type
                    )  # Check compatibility based on logical groups rather than exact match
                )
                if not is_valid:
                    mismatches.append(
                        f"{col}: {current_type} (expected {exp_type})"
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
            current_rows,
            expected_rows,
            row_diff_info,
            var_status,
            current_vars,
            expected_vars,
            var_diff_info,
            schema_ok,
            missing,
            extra,
            mismatches,
        )

        return row_status == "OK" and var_status == "OK" and schema_ok

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