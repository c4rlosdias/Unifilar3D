# Unifilar3D

**Unifilar3D** is a Python tool that generates a 3D unifilar (single-line diagram) representation of subsea pipeline IFC models.

It reads a source IFC model containing pipeline assemblies (`IfcBuilding` of type `SubseaPipeline`) and an IFC catalog of component types. For each pipeline, it fetches the 3D geometry representations of fitting and segment types from the catalog, assigns the correct materials and profiles, and lays out the components linearly along the X axis — spaced according to configurable gap parameters — producing a clean, linearized output IFC model ready for visualization or further processing.

## Features

- Matches `IfcPipeFittingType` and `IfcPipeSegmentType` against a reusable IFC catalog
- Clones geometry, material, and profile data from the catalog into the target model
- Generates pipe segment (tramo) geometry using material profile sets
- Configurable component gap (`dist`) and tramo gap (`dist_tramos`)
- Interactive CLI menu with full configuration control
- Detailed logging to file, with optional verbose console output

## Requirements

Install dependencies with:

```bash
pip install -r requirements.txt
```

Main dependencies: `ifcopenshell`, `numpy`, `tqdm`

## Usage

```bash
python unifilar3D.py
```

An interactive menu will appear allowing you to configure all parameters before execution:

| Option | Description | Default |
|--------|-------------|---------|
| `[1]` | Input IFC model path | `./input/model.ifc` |
| `[2]` | IFC catalog path | `./input/catalog.ifc` |
| `[3]` | Output IFC model path | `./output/model_clone.ifc` |
| `[4]` | Log file path | `unifilar3D.log` |
| `[5]` | Verbose console output | `no` |
| `[6]` | Component gap — `dist` (m) | `0.5` |
| `[7]` | Tramo gap — `dist_tramos` (m) | `0.1` |

Press `[E]` to execute or `[Q]` to quit.

## Project Structure

```
Unifilar3D/
├── unifilar3D.py       # Main script
├── requirements.txt    # Python dependencies
├── input/
│   ├── model.ifc       # Source pipeline IFC model
│   ├── catalog.ifc     # IFC component type catalog
│   └── drawings/       # Drawing assets (CSS, shading styles)
└── output/
    └── model_clone.ifc # Generated unifilar IFC model
```
