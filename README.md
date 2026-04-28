# Unifilar3D

**Unifilar3D** is a web application (Streamlit) that generates a 3D unifilar (single-line diagram) representation of subsea pipeline IFC models.

It reads a source IFC model containing pipeline assemblies (`IfcBuilding` of type `SubseaPipeline`) and an IFC catalog of component types. For each pipeline, it fetches the 3D geometry representations of fitting and segment types from the catalog, assigns the correct materials and profiles, and lays out the components linearly along the X axis — spaced according to configurable gap parameters — producing a clean, linearized output IFC model ready for download, visualization, or further processing.

## Features

- Browser-based interface — no command line required
- Upload IFC model and catalog directly through the UI
- Matches `IfcPipeFittingType` and `IfcPipeSegmentType` against a reusable IFC catalog
- Clones geometry, material, and profile data from the catalog into the target model
- Generates pipe segment (tramo) geometry using material profile sets
- Configurable component gap (`dist`) and tramo gap (`dist_tramos`)
- Real-time progress bar and status updates during processing
- Expandable log output panel with optional verbose mode
- One-click download of the generated IFC model

## Requirements

Install dependencies with:

```bash
pip install -r requirements.txt
```

Main dependencies: `streamlit`, `ifcopenshell`, `numpy`

## Usage

```bash
streamlit run unifilar3D.py
```

The app will open in your default browser. Use the sidebar to:

| Parameter | Description | Default |
|-----------|-------------|---------|
| Input Model | Upload the source pipeline `.ifc` file | — |
| IFC Catalog | Upload the component type catalog `.ifc` file | — |
| Output filename | Name for the generated IFC file | `model_clone.ifc` |
| Component gap — `dist` (m) | Spacing between components | `0.5` |
| Tramo gap — `dist_tramos` (m) | Spacing between pipe segments | `0.1` |
| Verbose logging | Show debug-level log output | off |

Click **▶ Execute** to process the model, then download the result with the **⬇ Download output IFC** button.

## Project Structure

```
Unifilar3D/
├── unifilar3D.py       # Streamlit web application
├── requirements.txt    # Python dependencies
├── input/
│   ├── model.ifc       # Example source pipeline IFC model
│   ├── catalog.ifc     # Example IFC component type catalog
│   └── drawings/       # Drawing assets (CSS, shading styles)
└── output/             # Local output directory (CLI legacy)
```
