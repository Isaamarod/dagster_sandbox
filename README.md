# 🟤 Framework Bronze - Data Contracts 🚀

## 🎯 Objetivo del Proyecto
Este repositorio tiene como misión estandarizar la ingesta y validación de datos en la **Capa Bronze** del Data Lake. 

A través de un enfoque basado en **Data Contracts (YAML)** y el motor **Ibis**, el framework permite asegurar la integridad de los esquemas, detectar cambios disruptivos (*breaking changes*) y normalizar el acceso a **Impala/DuckDB**, garantizando que solo el dato validado prosiga hacia las capas Silver y Gold.

---

## 🏗️ ¿Qué hace el script launcher_bronze.sh?

El `launcher_bronze.sh` es un automatizador de entorno que realiza las siguientes tareas:

* **⚡ Configuración de UV**: Instala el gestor de paquetes más veloz de Python, eliminando problemas de lentitud con `pip`.
* **🐍 Entorno 3.11**: Crea un entorno virtual aislado (`.venv`) con la versión de Python recomendada para el stack de datos usando UV.
* **📊 Stack de Datos**: Instala y configura **Ibis Framework**, **DuckDB** para cómputo local eficiente e **Impala** para consultas en cluster.
* **🛠️ Estructura Consistente**: Despliega un árbol de directorios preparado para la escalabilidad del código.
* **🔐 Seguridad de Credenciales**: Genera un archivo `.env` para evitar que las contraseñas se suban accidentalmente al control de versiones.

---

## 📂 Estructura del Proyecto

Tras ejecutar el script, el repositorio quedará organizado de la siguiente forma:

📂 **.** (Raíz del proyecto en Cloudera)  
├── 📜 **launcher_bronze.sh** (Script de despliegue)  
├── 📖 **README.md** (Guía general de Git)  
└── 📂 **notebooks/** (Contenedor principal del framework)  
....├── 📂 **.venv/** (Entorno virtual con librerías)  
....├── 📂 **layers/** ....
....│.└── 📂 **bronze/** ....│
....│.......├── 📓 **run_bronze.ipynb** (Código de bronze)  
....│.......├── 🐍 **logic.py** (Funciones de validación)  
....│.......├── 🐍 **utils_bronze.py** (Conectores y helpers)  
....│.......├── 📂 **data_contracts/** (Definiciones YAML de tablas)  
....│.......│.......├──🏷️ **nombre_tabla.yaml** 

---

# 🚀 Guía de Puesta en Marcha
Sigue estos pasos detallados para configurar tu entorno en Cloudera.

## 🛠️ Fase 1: Preparación y Despliegue

### 1. Preparar Contratos
Antes de nada, termina de definir tus tablas en archivos **🏷️ YAML**. Estos archivos deben seguir el estándar de Data Contracts y serán los que el framework utilice para validar la estructura de tus datos.

### 2. Descargar Plantillas
* Accede al repositorio: [dagster_sandbox (healthdatamad_notebooks)](https://github.com/Isaamarod/dagster_sandbox/tree/healthdatamad_notebooks)
* Haz clic en el botón verde **Code -> Download ZIP**.
* Descomprime el archivo en tu ordenador.

### 3. Subida a Cloudera
1. Inicia sesión en **Cloudera** y entra en tu proyecto.
2. Sube los archivos que has descomprimido al explorador de archivos de tu proyecto.
* **Importante:** Necesitas subir el archivo `launcher_bronze.sh` y el contenido de la carpeta `layers`.

### 4. Ejecutar el Instalador
1. Ve a la parte superior derecha de la interfaz de tu proyecto en Cloudera y haz clic en el botón **Terminal Access**.
2. En la terminal que se abre, escribe y ejecuta exactamente estos dos comandos:

```bash
# 1. Dar permisos de ejecución al script
chmod +x ./launcher_bronze.sh

# 2. Desplegar la estructura de carpetas y el entorno virtual
./launcher_bronze.sh
```
✨ ¡Resultado! El script habrá creado automáticamente la carpeta /notebooks con todo el stack técnico listo (Ibis, DuckDB, UV y Python 3.11).

## ⚙️ Fase 2: Configuración del Laboratorio
### 5. Configurar Credenciales
En el explorador de archivos de Cloudera, activa el switch "Show hidden files" (ubicado abajo a la derecha).

Localiza el archivo notebooks/.env e introduce tus credenciales de acceso a Impala.

Nota: Este archivo es personal y no debe compartirse.

### 6. Cargar Lógica y Contratos
🏷️ Contratos: Sube tus archivos YAML terminados a la ruta:

notebooks/layers/bronze/data_contracts/

🐍 Lógica Actualizada: Sustituye el archivo utils_bronze.py que está dentro de notebooks/layers/bronze/ por el que te has descargado del ZIP original (es el que contiene los conectores actualizados).

### 7. Ejecución (Orquestador)
Abre el archivo notebooks/layers/bronze/run_bronze.ipynb.

Este notebook es la plantilla operativa con todas las operaciones y los imports ya configurados.

Localiza la celda de configuración y sustituye los valores por el nombre de la tabla o tablas de tu Caso de Uso (CU) que definiste en los YAML.

Ejecuta las celdas y verifica que el contrato es válido y los datos se cargan correctamente. 🏁
