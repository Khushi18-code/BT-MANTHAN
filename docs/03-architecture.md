# Technical Architecture

## Layer Diagram

```mermaid
flowchart TD
    subgraph SOURCES[Data Sources]
        A1[HYCOM model output]
        A2[Copernicus Marine products]
        A3[Argo observations]
    end

    subgraph INGEST[Ingestion Layer]
        B1[NetCDF parser — xarray]
        B2[Delimited text parser]
    end

    subgraph PROCESS[Processing Layer]
        C1[Validation]
        C2[Normalization to common schema]
        C3[Provenance attachment]
        C4[Quality checks]
    end

    subgraph STORE[Storage Layer]
        D1[Scientific data store]
        D2[Metadata index & cache]
    end

    subgraph SERVE[Serving Layer]
        E1[REST API]
        E2[Spatial / temporal / depth subsetting]
        E3[Response cache]
    end

    subgraph CLIENT[Browser Client]
        F1[3D viewer — Three.js / WebGL]
        F2[Map & observation markers]
        F3[Profile & comparison charts]
        F4[Provenance, quality & analysis panels]
    end

    A1 --> B1
    A2 --> B1
    A3 --> B2
    B1 --> C1
    B2 --> C1
    C1 --> C2 --> C3 --> C4
    C4 --> D1
    C4 --> D2
    D1 --> E2
    D2 --> E2
    E2 --> E3 --> E1
    E1 --> F1
    E1 --> F2
    E1 --> F3
    E1 --> F4
```

## Why a Backend Is Necessary

Massive ocean datasets are stored as NetCDF — a binary scientific container format. A browser cannot
read it. Beyond format, there is scale: a single model field spans many depth levels, a wide grid and
many time steps, and the full dataset runs to gigabytes.

The backend is the translator and the subsetter. It opens the dataset with xarray, extracts exactly
the requested variable, region, depth window and time window — without materializing the whole file —
and returns web-ready JSON sized for the browser.

**Rule: never send giant NetCDF files to the browser.**

## Request Path

```mermaid
sequenceDiagram
    participant U as User
    participant C as Browser Client
    participant A as Backend API
    participant X as xarray Subsetter
    participant S as Data Store
    participant K as Cache

    U->>C: Selects region, variable, depth, time
    C->>A: GET /api/model-field?variable=TEMP&depth=340&region=...
    A->>K: Check cache
    alt Cache hit
        K-->>A: Cached JSON
    else Cache miss
        A->>X: Request subset
        X->>S: Read only required slice
        S-->>X: Subset data
        X-->>A: Values + coordinates + metadata
        A->>K: Store response
    end
    A-->>C: JSON with data, units, provenance, quality
    C-->>C: Update 3D shader, charts and panels
```

Caching matters beyond speed: repeated requests for the same region and depth combination should not
repeatedly load the upstream infrastructure.

## Subsystem Responsibilities

| Subsystem | Responsibility |
|---|---|
| Ingestion | Parse NetCDF and delimited text into a common internal representation |
| Validation | Reject or flag records failing structural and plausibility checks |
| Normalization | Unify variable names, units, coordinate and time conventions across sources |
| Provenance | Attach source, platform, processing and retrieval metadata to every returned value |
| Storage | Hold scientific data and a metadata/index layer for fast lookup |
| Serving | Expose REST endpoints with subsetting and caching |
| Client | Render 3D field, markers, profiles, comparison and analysis in the browser |

## Source-Specific Handling

HYCOM and Copernicus Marine do not share identical schemas, coordinates, units, metadata or
time/depth conventions. The ingestion layer treats each source explicitly rather than assuming
structural equivalence — a shared interface, separate adapters.

## Deployment

Static frontend and Python backend deployed together via Render. The browser client carries no
client-side dependencies beyond the served assets, so deployment on institutional infrastructure
requires no end-user installation.
