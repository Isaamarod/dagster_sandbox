import logging
import yaml
import re
from pathlib import Path
import ibis

def get_last_row_count(log_file: Path) -> int | None:
    """This function reads the log file if it exists and extracts the last row count from it.
    It looks for lines that contain either 'rows' (indicating a correct log entry) or 'Actual'
    (indicating a mismatch) and captures the number following those keywords. If the log file
    does not exist or if there is an error during reading, it returns None.
    
     Args:
        log_file (Path): The path to the log file from which to extract the last row count.
    
     Returns:
        int | None: The last row count extracted from the log file, or None if the file does
        not exist or if there is an error during reading."""
    
    # Verify if the log file exists; if not, return None
    if not log_file.exists():
        return None
    
    # Compile a regex pattern to match lines that contain either "rows" or "Actual" followed by a number
    pattern = re.compile(r"(\d+)\srows|Actual\s(\d+)") 
    
    # Initialize last_count to None; it will be updated if a valid line is found in the log file
    last_count = None
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                matches = pattern.findall(line)
                for match in matches:
                    # Extract the number from the matched line
                    val = match[0] if match[0] else match[1]
                    last_count = int(val)
    # If there is any exception during file reading or regex matching, return None
    except Exception:
        return None
    
    return last_count

def log_table_configurer(table_name: str, log_output_dir: Path) -> tuple[logging.Logger, logging.FileHandler, Path, int | None]:
    """This function configures a logger for a specific table. It creates a log file for the table
    in the specified output directory and sets up a logger that writes to that file. It also retrieves
    the last row count from the log file before configuring the logger, which can be used for comparison in subsequent runs.
    
     Args:
        table_name (str): The name of the table for which to configure the logger.
        log_output_dir (Path): The directory where the log file will be created.
    Returns:
        tuple: A tuple containing the configured logger, the file handler, the path to the log file,
        and the last row count extracted from the log file (or None if the file does not exist or if there was an error)."""
    
    # Ensure the log output directory exists; if not, create it
    log_file = log_output_dir / f"{table_name}.log"
    
    # Get the last row count from the log file (if it exists) to compare with the current count later
    previous_rows = get_last_row_count(log_file)
    
    # Configure the logger for the specific table
    logger = logging.getLogger(table_name)
    logger.setLevel(logging.INFO)
    if logger.hasHandlers():
        logger.handlers.clear()
    
    # Mode 'a' is used to append to the log file if it already exists
    file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger, file_handler, log_file, previous_rows

def log_multiples_tables_ibis(
        client: ibis.BaseBackend,
        table_list: list[str],
        database_name: str,
        contract_dir: Path,
        log_output_dir: Path
        ):
    """This function iterates over a list of table names, loads the corresponding data contracts from YAML files,
    and logs the actual row counts compared to the expected row counts defined in the contracts. It also handles
    logging of any mismatches and keeps track of the previous row counts for comparison in subsequent runs.
    
     Args:
        client (ibis.BaseBackend): An instance of an Ibis backend client used to connect to the database and execute queries.
        table_list (list[str]): A list of table names to process.
        database_name (str): The name of the database where the tables are located.
        contract_dir (Path): The directory where the YAML data contracts are stored.
        log_output_dir (Path): The directory where the log files will be created.""
        
    Returns:
        None: This function does not return any value; it performs logging as a side effect."""
    
    print("Starting the logging process for multiple tables...")

    # Ensure the log output directory exists; if not, create it
    log_output_dir.mkdir(parents=True, exist_ok=True)

    # Iterate over each table in the provided list and perform logging and comparison of row counts
    for table_name in table_list:
        
        print(f"\n\tProcessing table: {table_name}")

        # Initialize logger and handler to None; they will be configured later if the contract is successfully loaded
        logger, handler = None, None

        # --- Contract Loading and verification ---
        yaml_path = contract_dir / f"{table_name}.yaml"
        if not yaml_path.exists():
            print(f"\t\t⚠️ Warning: No contract (.yaml) found for {table_name}")
            continue

        try:
            # --- Load the contract to get the expected number of rows ---
            with open(yaml_path, 'r') as file:
                contract = yaml.safe_load(file)

            # --- Get expected row count from the contract ---
            n_expected_rows = contract.get("expected_rows")
            if n_expected_rows is None:
                print(f"\t\t⚠️ Warning: 'expected_rows' not found in contract for {table_name}")
                continue

            # --- Get actual row count ---
            # n_actual_rows = client.table(table_name, database=database_name).count().execute() #TODO: CAMBIAR LA SIMULACIÓN POR UNA CONEXIÓN REAL A LA BASE DE DATOS
            n_actual_rows = 10600 

            # --- Configure logger and get previous row count ---
            logger, handler, log_path, n_previous_rows = log_table_configurer(table_name, log_output_dir)

            # --- Log logic ---
            if n_actual_rows == n_expected_rows:
                logger.info(f"Table: {table_name} OK: {n_actual_rows} rows.")
            else:
                logger.warning(f"Table: {table_name} MISMATCH: Actual {n_actual_rows}, Expected {n_expected_rows}")

            # --- Print logic (With difference vs previous) ---
            diff_text = ""
            if n_previous_rows is not None:
                diff = n_actual_rows - n_previous_rows
                simbolo = "+" if diff > 0 else ""
                diff_text = f"(Dif. vs previous: {simbolo}{diff})"
            else:
                diff_text = "(No previous data - First run)"

            # Print if the result is OK or MISMATCH
            print(f"\t\t{'✅ OK' if n_actual_rows == n_expected_rows else '⚠️ MISMATCH'}: Actual Rows: {n_actual_rows} | Expected Rows: {n_expected_rows} | {diff_text}")

        except Exception as e:
            if logger:
                logger.error(f"Failed to process table '{table_name}': {e}")
            print(f"❌ Table '{table_name}' failed: {e}")
        
        finally:
            if handler:
                handler.close()
            if logger and handler:
                logger.removeHandler(handler)


c_dir = Path("./data_contracts")
l_dir = Path("./logs_n_rows_tablas")
log_multiples_tables_ibis(None, ["cibeles_historico", "AAA"], "db", c_dir, l_dir) # type: ignore