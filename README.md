# Dagster Sandbox

This repository is a working environment designed to learn and build a modern data pipeline using:

- **Dagster** for orchestration
- **uv** for virtual environment and dependency management

The first implementation (`main` branch) focuses on:

- Installing and running Dagster locally or in a remote environment (e.g. Cloudera)
- Creating core project structure
- Defining simple assets and jobs without external data connections

A separate branch will later introduce:

- Ibis-based ingestion from Impala
- Bronze → Silver → Gold data layering
- Data quality checks and resource configurations

---

## 🚀 Objectives

- Set up Dagster using `uv`
- Create basic Dagster assets and jobs that run via CLI
- Prepare a clean project structure that can evolve
- Design a branching strategy for incremental feature development

---

## 🧠 Branching Strategy

- `main`  
  Minimal Dagster setup. No Impala or Ibis.

- `feature/impala-ibis-ingestion`  
  Extends the project with Ibis-based extraction from Impala and a domain-layered architecture.

Additional branches may include:

- `feature/data-quality`
- `feature/dbt-transformations`
- `feature/metrics-and-dashboards`

This approach keeps changes incremental, traceable, and review-friendly.

---

## 🧱 Requirements

- Linux, macOS, or a cloud terminal (e.g. Codespaces, Cloudera session)
- `curl`
- Internet connectivity for installing `uv`

---

## 🛠 Installation

### 1. Install `uv`

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Reload:

```bash
source ~/.bashrc
```

Check:

```bash
uv --version
```

---

### 2. Initialize the project

```bash
uv init
uv sync
```

---

### 3. Install Dagster

```bash
uv add dagster dagster-webserver dagster-dg-cli
```

---

### 4. Start Dagster in development mode

```bash
dg dev
```

Open in a browser:

```
http://localhost:3000
```

---

## 📂 Recommended Project Structure

```
dagster_sandbox/
│
├─ dagster_sandbox/
│   ├─ __init__.py
│   ├─ assets/
│   ├─ jobs/
│   ├─ resources/
│   └─ definitions.py
│
├─ pyproject.toml
├─ .venv/
└─ README.md
```

The structure allows future expansion into domain-based modules such as:

- `ingestion`
- `transform`
- `analytics`

---

## 🔜 Upcoming Features (separate branch)

Planned in `feature/impala-ibis-ingestion`:

- Connection to Impala via Ibis
- Bronze-level raw data extraction
- Silver/Gold transformations
- Data quality checks (Great Expectations, Pandera, or similar)

---

## 📅 Roadmap

- [x] Base Dagster installation
- [x] Minimal project layout
- [ ] Add Impala + Ibis workflow (new branch)
- [ ] Implement data quality validation
- [ ] Add dashboards or analytical outputs

---

## 📄 License

Free for educational and experimental use.

