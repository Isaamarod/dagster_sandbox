#!/bin/bash

# --- CONFIGURACIÓN ---
PROJECT_NAME="PROYECTO_HEALTHDATAMAD_NOTEBOOKS"

echo "🚀 Iniciando creación del proyecto: $PROJECT_NAME"

# 1. INSTALACIÓN DE UV (Si no existe)
if ! command -v uv &> /dev/null
then
    echo "⚠️ 'uv' no encontrado. Instalando mediante pip..."
    pip install uv
fi

# 2. CREACIÓN DE ESTRUCTURA
echo "📂 Creando carpetas y archivos dentro de /notebooks..."
mkdir -p notebooks/layers/bronze/data_contracts
touch notebooks/layers/bronze/__init__.py
touch notebooks/layers/bronze/logic.py
touch notebooks/layers/bronze/utils_bronze.py
touch notebooks/layers/bronze/run_bronze.ipynb

# 3. CONFIGURACIÓN .ENV (Dentro de notebooks)
if [ ! -f notebooks/.env ]; then
    cat << 'EOF' > notebooks/.env
IMPALA_HOST=
IMPALA_PORT=21050
IMPALA_USER=
IMPALA_PASSWORD=
IMPALA_HTTP_PATH=
EOF
    echo "✅ Archivo .env creado en notebooks/."
fi

# 4. GESTIÓN DE PROYECTO CON UV (Entramos en notebooks)
cd notebooks
echo "🛠️ Inicializando proyecto uv dentro de /notebooks..."
# Usamos --app para evitar la carpeta /src
uv init --app --name $PROJECT_NAME

# 5. INSTALACIÓN DE LIBRERÍAS
echo "📦 Instalando dependencias en notebooks/.venv..."
uv add \
    "python-dotenv>=1.2.1" \
    "ibis-framework[duckdb,impala]" \
    "pyyaml" \
    "ipykernel"

# Sincronizar y limpiar archivos que sobran
uv sync
rm -f hello.py
rm -f main.py

# 6. GENERACIÓN DEL README (Dentro de notebooks)
cat << 'EOF' > README.md
# 🟤 Framework Bronze (Notebooks Edition)

Toda la lógica, el entorno virtual y la ejecución están centralizados en este directorio.

## 📂 Estructura Interna
- **.venv/**: Entorno virtual del proyecto (gestionado por UV).
- **pyproject.toml**: Archivo de configuración y dependencias.
- **layers/bronze/**: Lógica y contratos de datos.
- **run_bronze.ipynb**: Punto de ejecución.
- **.env**: Credenciales de Impala.

## 🚀 Uso
1. Rellena el archivo `.env`.
2. Activa el entorno: `source .venv/bin/activate`.
3. Define tus contratos YAML en `layers/bronze/data_contracts/`.
4. Ejecuta `run_bronze.ipynb`.
EOF

cd .. # Volvemos a la raíz para el mensaje de cierre

echo "--------------------------------------------------"
echo "✅ ¡Proyecto listo!"
echo "📍 Todo se ha concentrado en la carpeta: /notebooks"
echo "--------------------------------------------------"
echo "💡 Para activar el entorno, ejecuta:"
echo "   source notebooks/.venv/bin/activate"
echo "--------------------------------------------------"