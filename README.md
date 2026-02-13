# 🟤 Framework Bronze - Data Contracts 🚀

## 🎯 Objetivo del Proyecto
Este repositorio tiene como misión estandarizar la ingesta y validación de datos en la **Capa Bronze** del Data Lake. 

A través de un enfoque basado en **Data Contracts (YAML)** y el motor **Ibis**, el framework permite asegurar la integridad de los esquemas, detectar cambios disruptivos (*breaking changes*) y normalizar el acceso a **Impala/DuckDB**, garantizando que solo el dato validado prosiga hacia las capas Silver y Gold.

---

## 🏗️ ¿Qué hace el script launcher_bronze.sh?

El `launcher.sh` es un automatizador de entorno que realiza las siguientes tareas:

* **⚡ Configuración de UV**: Instala el gestor de paquetes más veloz de Python, eliminando problemas de lentitud con `pip`.
* **🐍 Entorno 3.11**: Crea un entorno virtual aislado (`.venv`) con la versión de Python recomendada para el stack de datos usando UV.
* **📊 Stack de Datos**: Instala y configura **Ibis Framework**, **DuckDB** para cómputo local eficiente e **Impala** para consultas en cluster.
* **🛠️ Estructura Consistente**: Despliega un árbol de directorios preparado para la escalabilidad del código.
* **🔐 Seguridad de Credenciales**: Genera un archivo `.env` para evitar que las contraseñas se suban accidentalmente al control de versiones.

---

## 📂 Estructura del Proyecto

Tras ejecutar el script, el repositorio quedará organizado de la siguiente forma:

📂 **.** (Raíz del proyecto)  
├── 📜 **launcher_bronze.sh** (Script de despliegue)  
├── 📖 **README.md** (Guía general de Git)  
└── 📂 **notebooks/** (Contenedor principal del framework)  
....├── 📂 **.venv/** (Entorno virtual con librerías)  
....├── 📂 **layers/** ....│...└── 📂 **bronze/** ....│.......├── 📂 **data_contracts/** (Definiciones YAML de tablas)  
....│.......├── 🐍 **logic.py** (Funciones de validación)  
....│.......└── 🐍 **utils_bronze.py** (Conectores y helpers)  
....├── 📓 **run_bronze.ipynb** (Orquestador interactivo)  
....├── 📜 **pyproject.toml** (Manifiesto de dependencias UV)  
....├── 🔒 **uv.lock** (Bloqueo de versiones)  
....├── 📄 **.env** (Configuración de credenciales)  
....└── 📖 **README.md** (Guía técnica para el desarrollador)



---

### 💡 ¿Por qué esta organización?
* **Aislamiento**: Todo lo necesario para ejecutar el proceso vive dentro de `/notebooks`.
* **Simplicidad**: Permite importaciones directas desde los notebooks sin configurar el `sys.path`.
* **Calidad**: Obliga a separar la definición del dato (YAML) de la lógica de procesamiento (Python).

---
