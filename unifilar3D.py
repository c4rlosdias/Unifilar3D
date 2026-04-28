import ifcopenshell
from ifcopenshell import geom
from ifcopenshell.util import representation, element, selector, placement, shape
from ifcopenshell.api import type, geometry, context, style, material
import numpy as np
import logging
import io
import os
import tempfile
from pathlib import Path
import streamlit as st

DEFAULT_MODEL_INPUT   = "./input/model.ifc"
DEFAULT_CATALOG_INPUT = "./input/catalog.ifc"
DEFAULT_MODEL_OUTPUT  = "./output/model_clone.ifc"
DEFAULT_LOG_FILE      = "unifilar3D.log"
DEFAULT_DIST          = 0.5
DEFAULT_DIST_TRAMOS   = 0.1


def clone_entity(elements : list, model : ifcopenshell.file, sub_context : ifcopenshell.entity_instance) -> list:
    """
    Clone the given elements and assign the sub_context to the ContextOfItems attribute of the cloned elements.
    """
    new_elements = []
  
    if sub_context is not None:
        for element in elements:            
            new_element = model.create_entity(element.is_a())
            for attribute, value in element.__dict__.items():                
                if attribute not in ['id', 'type', 'attributes']:
                    # if attribute is equal to ContextOfItems, set it to the sub_context
                    if attribute == 'ContextOfItems':
                        setattr(new_element, attribute, sub_context)
                    # if attribute is a entity instance, clone the entity instance
                    elif isinstance(value, ifcopenshell.entity_instance):
                        setattr(new_element, attribute, clone_entity([value], model, sub_context)[0])
                    # if attribute is a list of entity instances, clone each entity instance in the list
                    elif isinstance(value, list) or isinstance(value, tuple):
                        if len(value) > 0 and isinstance(value[0], ifcopenshell.entity_instance):
                            setattr(new_element, attribute, clone_entity(list(value), model, sub_context))
                        else:
                            setattr(new_element, attribute, value)
                    else:
                        setattr(new_element, attribute, value)    

            new_elements.append(new_element)          

        return new_elements
    else:
        return None

def get_type_catalog(type_name : str, catalog : ifcopenshell.file) -> ifcopenshell.entity_instance:
    """
    Get the type from the catalog with the given name.
    """
    types = catalog.by_type('IfcTypeProduct')
    for type in types:
        if type.Name == type_name:
            return type
    return None

def get_material_catalog(type_catalog : ifcopenshell.entity_instance) -> ifcopenshell.entity_instance:
    """
    Get the material from the catalog with the given name.
    """
    catalog = type_catalog.file
    sub_context = representation.get_context(catalog, 'Model', 'Body', 'MODEL_VIEW')  
    material_type = element.get_material(type_catalog)

    if material_type is not None:
        if material_type.is_a('IfcMaterial'):
            style_type = representation.get_material_style(material_type, sub_context)
            if style_type is not None:
                return material_type, style_type, None
            else:
                return material_type, None, None
        
        elif material_type.is_a('IfcMaterialProfileSet'):
            profile_type = material_type.MaterialProfiles[0].Profile
            material_type = material_type
            style_type = representation.get_material_style(material_type.MaterialProfiles[0].Material, sub_context)
           
            if style_type is not None:
                return material_type, style_type, profile_type
            else:
                return material_type, None, profile_type
            
    else:
        return None, None, None

def make_new_material(model : ifcopenshell.file, material_type : ifcopenshell.entity_instance, style_type : ifcopenshell.entity_instance, profile_type : ifcopenshell.entity_instance, sub_context : ifcopenshell.entity_instance) -> ifcopenshell.entity_instance:
    """
    Clone the material, style and profile from the catalog and assign the style to the material and the material to the profile.
    """
    # verifies if the material already exists in the model, if it does, assign it to the type target, if it doesn't, clone the material and assign it to the type target
    target_material = selector.filter_elements(model, f"{material_type.is_a()}, Name=/{material_type.Name}/")
    if len(target_material) > 0:
        logging.debug(f'{material_type.Name} : existing material found and assigned successfully! ({list(target_material)[0]})')
        return list(target_material)[0]

    logging.warning(f'{material_type.Name} : material not found in model, creating new material!')

    if material_type.is_a('IfcMaterial'):
        logging.debug(f'{material_type.Name} : material type is IfcMaterial, cloning material and style from catalog...')
        material_entity = material_type
    elif material_type.is_a('IfcMaterialProfileSet'):
        logging.debug(f'{material_type.Name} : material type is IfcMaterialProfileSet, cloning material, style and profile from catalog...')
        material_entity = material_type.MaterialProfiles[0].Material
    else:
        logging.error(f'{material_type.Name} is not IfcMaterial neither IfcMaterialProfileSet type, cannot clone material!')
        return None

    new_material = clone_entity([material_entity], model, sub_context)[0]

    if style_type is not None:
        new_style = clone_entity([style_type], model, sub_context)[0]
        style.assign_material_style(model, material=new_material, style=new_style, context=sub_context)
    else:
        logging.error(f'Material {material_type.Name} : material style not found in catalog!')

    if material_type.is_a('IfcMaterial'):
        return new_material

    # IfcMaterialProfileSet: create profile set
    if profile_type is not None:
        new_profile = clone_entity([profile_type], model, sub_context)[0]
        material_set = material.add_material_set(model, name=f'{new_material.Name}', set_type='IfcMaterialProfileSet')
        material.add_profile(model, profile_set=material_set, material=new_material, profile=new_profile)
        logging.debug(f'{material_type.Name} of type {material_type.is_a()} : new material created and assigned successfully! ({material_set})')
        return material_set
    else:
        logging.error(f'Material {material_type.Name} : material profile not found in catalog!')
        return None
        
    
def add_catalog_representation(type_target : ifcopenshell.entity_instance, model : ifcopenshell.file, catalog_input : str) -> list:
    """
    Clone the representation map of the given type target.
    """
    sub_context = representation.get_context(model, 'Model', 'Body', 'MODEL_VIEW')  
    if sub_context is None:
        sub_context = context.add_context(model, context_type='Model', context_identifier='Body')
    catalog = ifcopenshell.open(catalog_input)

    type_catalog = get_type_catalog(type_target.Name, catalog)
    
    if type_catalog is None:
        return False
    
    catalog_representation_map = type_catalog.RepresentationMaps
    if catalog_representation_map is not None:
        target_representation_map = clone_entity(catalog_representation_map, model, sub_context)
        type_target.RepresentationMaps = target_representation_map

    type_material, type_style, type_profile = get_material_catalog(type_catalog)
    
    if type_material is not None:        
        new_material = make_new_material(model, type_material, type_style, type_profile, sub_context)        
        material.assign_material(model, products=[type_target], type=new_material.is_a(), material=new_material)
            
    else:
        logging.warning(f'{type_target.Name} - {type_material.Name} : material not found in catalog!')
        
    return True

def create_pipe(model : ifcopenshell.file, tramo : ifcopenshell.entity_instance, position : tuple, depth : float) -> ifcopenshell.entity_instance:
    """
    Create a pipe representation for the given tramo.
    """
    sub_context = representation.get_context(model, 'Model', 'Body', 'MODEL_VIEW')  
    if sub_context is None:
        sub_context = context.add_context(model, context_type='Model', context_identifier='Body')
    
    # create a new representation for the tramo
    element_type=element.get_type(tramo)

    if element_type is not None:       
       material_set = element.get_material(element_type)
       if material_set is not None and material_set.is_a('IfcMaterialProfileSet'):            
            profile = material_set.MaterialProfiles[0].Profile 
            matrix = np.eye(4)
            matrix[:,3][0:3] = (position[0], position[1], 0)
            geometry.edit_object_placement(model, product=tramo, matrix=matrix, is_si=True)
            represent = geometry.add_profile_representation(
                model,
                context=sub_context,
                profile=profile,
                depth=depth,
                placement_zx_axes=((1.0, 0.0, 0.0),(0.0, 0.0, 1.0))
            )
            geometry.assign_representation(model, product=tramo, representation=represent)

            return True    
       else:
           return None
    else:
        return None


def run_processing(model_path, catalog_path, dist, dist_tramos, log_buffer, progress_bar, status_text):
    """Run the full IFC unifilar processing pipeline."""

    model = ifcopenshell.open(model_path)
    settings = geom.settings()

    # --- Types ---
    types = model.by_type('IfcPipeFittingType') + model.by_type('IfcPipeSegmentType')
    total_types = len(types)
    logging.info('Initiating processing of types representation map from catalog...')

    for i, type_target in enumerate(types):
        status_text.text(f"Processing type {i + 1}/{total_types}: {type_target.Name}")
        progress_bar.progress((i + 1) / total_types if total_types else 1.0, text="Processing types...")
        logging.debug(f'Processing Type {type_target.id()} - {type_target.Name}...')

        if add_catalog_representation(type_target, model, catalog_path):
            instances = element.get_types(type_target)
            for instance in instances:
                geometry.edit_object_placement(model, product=instance)
            type.unassign_type(model, related_objects=list(instances))
            type.assign_type(model, related_objects=list(instances), relating_type=type_target)
        else:
            logging.debug(f'Type {type_target.Name} not found in catalog!')

    # --- Buildings / Tramos ---
    buildings = model.by_type('IfcBuilding')
    total_buildings = len(buildings)

    for b_idx, building in enumerate(buildings):
        status_text.text(f"Processing building {b_idx + 1}/{total_buildings}: {building.Name}")
        progress_bar.progress((b_idx + 1) / total_buildings if total_buildings else 1.0, text="Processing buildings...")

        if building.ObjectType != 'SubseaPipeline':
            continue

        logging.info(f'Processing Building {building.id()} - {building.Name}...')

        x = 0
        x_start = 0
        y = 0

        for tramo in element.get_contained(building):
            logging.info(f'Processing Tramo {tramo.id()} - {tramo.Name}...')
            components = element.get_components(tramo)
            n = len(components)
            x_start = x
            first_tam = 0
            depth = 0

            for i, component in enumerate(components):
                component_type = element.get_type(component)

                if component.Representation is not None:
                    component_shape = geom.create_shape(settings, component)
                    verts = np.array(component_shape.geometry.verts).reshape(-1, 3)
                    tam = float(verts[:, 0].max() - verts[:, 0].min())
                    logging.debug(f'Component {component.id()} - {component.Name}: width = {tam:.3f} m')
                else:
                    logging.warning(f'Component {component.id()} - {component.Name}: no representation, defaulting to {dist} m')
                    tam = dist

                if i == 0:
                    first_tam = tam

                y = -dist if component_type.ElementType == 'PipePullingHeadType' else 0

                matrix = np.eye(4)
                if i + 1 > n / 2:
                    matrix = placement.rotation(180, "Z") @ matrix
                    x += tam

                matrix[:3, 3] = (x, y, 0)
                geometry.edit_object_placement(model, product=component, matrix=matrix, is_si=True)
                logging.info(f'Component {component.id()} - {component.Name} ({component_type.ElementType}) placed at x={x:.3f}')

                depth = x - x_start - 2 * tam
                x += tam + dist

            x += dist_tramos - (tam + dist)
            create_pipe(model, tramo, (x_start + first_tam, y), depth)

    # Write output to a bytes buffer via a temp file
    with tempfile.NamedTemporaryFile(suffix=".ifc", delete=False) as tmp_out:
        tmp_out_path = tmp_out.name

    try:
        model.write(tmp_out_path)
        with open(tmp_out_path, "rb") as f:
            return f.read()
    finally:
        try:
            os.remove(tmp_out_path)
        except OSError:
            pass


def main():
    st.set_page_config(
        page_title="Unifilar3D",
        page_icon="🏗️",
        layout="wide",
    )

    st.title("Unifilar3D — IFC Unifilar Representation Generator")

    # ── Sidebar: configuration ──────────────────────────────────────────────
    with st.sidebar:
        st.header("Configuration")

        model_file   = st.file_uploader("Input Model (.ifc)", type=["ifc"], key="model_file")
        catalog_file = st.file_uploader("IFC Catalog (.ifc)", type=["ifc"], key="catalog_file")

        st.divider()

        output_name  = st.text_input("Output filename", "model_clone.ifc")
        dist         = st.number_input("Component gap — dist (m)", value=DEFAULT_DIST,        min_value=0.0, step=0.05, format="%.3f")
        dist_tramos  = st.number_input("Tramo gap — dist_tramos (m)", value=DEFAULT_DIST_TRAMOS, min_value=0.0, step=0.01, format="%.3f")
        verbose      = st.checkbox("Verbose logging")

        st.divider()
        execute = st.button("▶ Execute", type="primary", use_container_width=True)

    # ── Main area ───────────────────────────────────────────────────────────
    if not execute:
        st.info("Upload the input model and catalog in the sidebar, adjust parameters, then click **Execute**.")
        return

    if model_file is None or catalog_file is None:
        st.error("Please upload both the **Input Model** and the **IFC Catalog** before executing.")
        return

    # Save uploaded files to a temporary directory
    with tempfile.TemporaryDirectory() as tmpdir:
        model_path   = os.path.join(tmpdir, model_file.name)
        catalog_path = os.path.join(tmpdir, catalog_file.name)

        with open(model_path, "wb") as f:
            f.write(model_file.read())
        with open(catalog_path, "wb") as f:
            f.write(catalog_file.read())

        # Configure logging to capture into a string buffer
        log_buffer = io.StringIO()
        log_handlers = [logging.StreamHandler(log_buffer)]
        logging.basicConfig(
            level=logging.DEBUG if verbose else logging.INFO,
            format="%(asctime)s %(levelname)s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            handlers=log_handlers,
            force=True,
        )

        progress_bar = st.progress(0, text="Starting...")
        status_text  = st.empty()
        output_bytes = None

        try:
            with st.spinner("Processing IFC model…"):
                output_bytes = run_processing(
                    model_path, catalog_path,
                    dist, dist_tramos,
                    log_buffer, progress_bar, status_text,
                )
            progress_bar.progress(1.0, text="Done!")
            status_text.text("Processing complete.")
            st.success("Model processed successfully!")
        except Exception as exc:
            st.error(f"Processing failed: {exc}")
            logging.exception("Unhandled exception during processing")

        # Log output
        with st.expander("Log output", expanded=verbose):
            st.text(log_buffer.getvalue() or "(no log output)")

        # Download button
        if output_bytes is not None:
            st.download_button(
                label="⬇ Download output IFC",
                data=output_bytes,
                file_name=output_name,
                mime="application/octet-stream",
            )


if __name__ == "__main__":
    main()

