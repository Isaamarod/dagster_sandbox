#!/bin/bash

# --- CONFIGURACIÓN ---
PROJECT_NAME="proyecto_healthdatamad_notebooks"
DISPLAY_NAME="HealthDataMADEnv"

echo "🚀 Iniciando creación del proyecto: $PROJECT_NAME"

# 1. INSTALACIÓN DE UV (Si no existe)
if ! command -v uv &> /dev/null
then
    echo "⚠️ 'uv' no encontrado. Instalando..."
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

# 4. GESTIÓN DE PROYECTO CON UV
cd notebooks
echo "🛠️ Inicializando proyecto uv..."
uv init --app --name $PROJECT_NAME

# 5. INSTALACIÓN DE LIBRERÍAS
# Incluimos ipykernel explícitamente para que el kernel funcione
echo "📦 Instalando dependencias (esto puede tardar un poco)..."
uv add \
    "python-dotenv>=1.2.1" \
    "ibis-framework[duckdb,impala]" \
    "pyyaml" \
    "ipykernel"

uv sync
rm -f hello.py # los eliminamos vienen por defecto
rm -f main.py

# 6. REGISTRO DEL KERNEL EN JUPYTER 🛰️
# Esto permite que el entorno aparezca en el desplegable de Jupyter automáticamente
echo "✨ Registrando el Kernel en Jupyter..."
uv run python -m ipykernel install --user --name "$PROJECT_NAME" --display-name "$DISPLAY_NAME"

# 7. GENERACIÓN DEL README
cat << 'EOF' > README.md
# 🟤 Framework Bronze (Notebooks Edition)
Toda la lógica, el entorno virtual y la ejecución están centralizados en este directorio.
## 📂 Estructura Interna
- **.venv/**: Entorno virtual del proyecto (gestionado por UV).
- **pyproject.toml**: Archivo de configuración y dependencias.
- **layers/bronze/**: Lógica y contratos de datos.
- **run_bronze.ipynb**: Punto de ejecución.
- **.env**: Credenciales de Impala.

## 🚀 Pasos a seguir 
1. Rellena el archivo `.env`.
2. Abre tu Jupyter Lab / Notebook.
3. **Selecciona el Kernel:** En la esquina superior derecha, elige **"$DISPLAY_NAME"**.
4. ¡Listo para ejecutar!
EOF

cd .. # Volvemos a la raíz

echo "--------------------------------------------------"
echo "✅ ¡Proyecto y Kernel configurados con éxito!"
echo "📍 Todo concentrado en la carpeta: /notebooks"
echo "🖥️  Kernel registrado: $DISPLAY_NAME"
echo "--------------------------------------------------"
echo "💡 Importante: Si usas VSCode o Jupyter, ya deberías"
echo "   ver el entorno disponible en la lista de Kernels."
echo "--------------------------------------------------"
