import ifcopenshell
from ifcopenshell import geom
from ifcopenshell.util import representation, element, selector, placement, shape
from ifcopenshell.api import type, geometry, context, style, material, spatial, nest
import numpy as np
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

dists = {
    "AnodeCollarSet-EndFitting" : 0.1,
    "EndFitting-AnodeCollarSet": 0.1,
}

def update_predefined_types(model : ifcopenshell.file):
    for entity in model.by_type('IfcElement'):
        if getattr(entity, 'IsTypedBy', None):
            entity_type = entity.IsTypedBy[0].RelatingType
            if getattr(entity_type, 'ElementType', None) is not None:
                object_type = entity_type.ElementType.replace("Type", "")
                object_type = object_type.replace("Structure", "Segment")
                entity.ObjectType = object_type
                entity.PredefinedType = None
                st.write(f'Updated predefined type for {entity.id()} - {entity.Name} to {entity.ObjectType}')

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

def get_type_catalog(type_attribute : str, attribute : str, catalog : ifcopenshell.file) -> ifcopenshell.entity_instance:
    """
    Get the type from the catalog with the given attribute value.
    """
    types = catalog.by_type('IfcTypeProduct')
    for type in types:
        if getattr(type, attribute, None) == type_attribute:
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
        st.write(f'{material_type.Name} : existing material found and assigned successfully! ({list(target_material)[0]})')
        return list(target_material)[0]

    st.warning(f'{material_type.Name} : material not found in model, creating new material!')

    if material_type.is_a('IfcMaterial'):
        st.write(f'{material_type.Name} : material type is IfcMaterial, cloning material and style from catalog...')
        material_entity = material_type
    elif material_type.is_a('IfcMaterialProfileSet'):
        st.write(f'{material_type.Name} : material type is IfcMaterialProfileSet, cloning material, style and profile from catalog...')
        material_entity = material_type.MaterialProfiles[0].Material
    else:
        st.error(f'{material_type.Name} is not IfcMaterial neither IfcMaterialProfileSet type, cannot clone material!')
        return None

    new_material = clone_entity([material_entity], model, sub_context)[0]

    if style_type is not None:
        new_style = clone_entity([style_type], model, sub_context)[0]
        style.assign_material_style(model, material=new_material, style=new_style, context=sub_context)
    else:
        st.error(f'Material {material_type.Name} : material style not found in catalog!')

    if material_type.is_a('IfcMaterial'):
        return new_material

    # IfcMaterialProfileSet: create profile set
    if profile_type is not None:
        new_profile = clone_entity([profile_type], model, sub_context)[0]
        material_set = material.add_material_set(model, name=f'{new_material.Name}', set_type='IfcMaterialProfileSet')
        material.add_profile(model, profile_set=material_set, material=new_material, profile=new_profile)
        st.write(f'{material_type.Name} of type {material_type.is_a()} : new material created and assigned successfully! ({material_set})')
        return material_set
    else:
        st.error(f'Material {material_type.Name} : material profile not found in catalog!')
        return None
        
    
def add_catalog_representation(type_target : ifcopenshell.entity_instance, model : ifcopenshell.file, catalog_input : str, attribute : str) -> list:
    """
    Clone the representation map of the given type target.
    """
    sub_context = representation.get_context(model, 'Model', 'Body', 'MODEL_VIEW')  
    if sub_context is None:
        sub_context = context.add_context(model, context_type='Model', context_identifier='Body')
    catalog = ifcopenshell.open(catalog_input)

    type_catalog = get_type_catalog(getattr(type_target, attribute, None), attribute, catalog)
    
    if type_catalog is None:
        st.warning(f'{type_target.Name} : type not found in catalog!')
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
        st.warning(f'{type_target.Name} - material not found in catalog!')
        
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

def get_connected(entity : ifcopenshell.entity_instance) -> list:
    """
    Get the connected elements of the given entity.
    """
    connected_elements = [
        rel.RelatingElement
        for rel in getattr(entity, 'ConnectedFrom', [])
        if hasattr(rel, 'RelatingElement') and rel.RelatingElement.ObjectType != "EndFitting"
    ]
    return connected_elements

def get_component_length(component : ifcopenshell.entity_instance) -> float:
    """
    Get the length of the given component from its representation.
    """
    if component.Representation is not None:
        component_shape = geom.create_shape(geom.settings(), component)
        verts = np.array(component_shape.geometry.verts).reshape(-1, 3)
        length = float(verts[:, 0].max() - verts[:, 0].min())
        return length
    else:
        return None
       
def run_processing(model_path, catalog_path, attribute, dist, dist_tramos, progress_bar, status_text):
    """Run the full IFC unifilar processing pipeline."""

    model = ifcopenshell.open(model_path)
    settings = geom.settings()

    # --- Initial placements for ports ---
    st.markdown(':green[Initiating processing of ports initial placements...]')
    ports = model.by_type('IfcDistributionPort')
    for port in ports:
        st.write(f'Processing Port {port.id()} - {port.Name}...')
        if port.ObjectPlacement is None:
            geometry.edit_object_placement(model, product=port)
    
    # --- Types ---
    st.markdown(':green[Initiating processing of types representation map from catalog...]')
    types = model.by_type('IfcPipeFittingType') + model.by_type('IfcPipeSegmentType')
    total_types = len(types)
    st.write('Initiating processing of types representation map from catalog...')

    # Iterate over types and add catalog representation map, then update placements of related instances
    for i, type_target in enumerate(types):
        status_text.text(f"Processing type {i + 1}/{total_types}: {type_target.Name}")
        progress_bar.progress((i + 1) / total_types if total_types else 1.0, text="Processing types...")
        st.write(f'Processing Type #{type_target.id()} - {type_target.Name}...')

        if add_catalog_representation(type_target, model, catalog_path, attribute):
            instances = element.get_types(type_target)
            for instance in instances:
                geometry.edit_object_placement(model, product=instance)
            type.unassign_type(model, related_objects=list(instances))
            type.assign_type(model, related_objects=list(instances), relating_type=type_target)
        else:
            st.write(f'Type {type_target.Name} not found in catalog!')

    # --- update predefined types (after type.assign_type to avoid being reset) ----
    st.markdown(':green[Updating predefined types...]')
    update_predefined_types(model)

    # --- Pipe Aggregations ---
    # st.markdown(':green[Initiating processing of aggregate initial placements...]')
    # subsea_pipeline = list(selector.filter_elements(model, "IfcBuilding, ObjectType=SubseaPipeline"))[0]
    # pipes = selector.filter_elements(model, "IfcPipeSegment")
    # for pipe in pipes:
    #     if pipe not in element.get_contained(subsea_pipeline) and pipe.ObjectType == 'FlexiblePipeSegment':
    #         st.write(f'Assigning #{pipe.id()} - {pipe.Name} to SubseaPipeline...')
    #         spatial.assign_container(model, products=[pipe], relating_structure=subsea_pipeline)

    
    # --- Buildings / Tramos ---
    st.markdown(':green[Initiating processing tramos of initial placements...]')
    buildings = model.by_type('IfcBuilding')
    total_buildings = len(buildings)

    for b_idx, building in enumerate(buildings):
        status_text.text(f"Processing building {b_idx + 1}/{total_buildings}: {building.Name}")
        progress_bar.progress((b_idx + 1) / total_buildings if total_buildings else 1.0, text="Processing buildings...")

        if building.ObjectType != 'SubseaPipeline':
            continue

        st.write(f'Processing Building {building.id()} - {building.Name}...')

        x = 0
        x_start = 0
        y = 0

        ###########################################
        aggregations = element.get_contained(building)
        tramos = element.get_components(aggregations[0])
        ###########################################

        for tramo in tramos:
            st.write(f'Processing Tramo #{tramo.id()} - {tramo.Name}...')
            try:
                components = element.get_components(tramo)
            except Exception as e:
                st.error(f'Error processing Tramo #{tramo.id()} - {tramo.Name}: {e}')
                continue
            
            # initialize variables for tramo processing
            n = len(components)
            x_start = x 
            first_tam = 0
            depth = 0
            tam = 0
            old_component = ''
            pullings = []

            st.write(f'Number of components in Tramo #{tramo.id()} - {tramo.Name}: {n}')
            # if no components, create a pipe with tramo gap length and continue to next tramo
            if len(components) == 0:
                st.warning(f'Tramo {tramo.id()} - {tramo.Name} has no components, defaulting to tramo gap {dist_tramos} m')
                x += dist_tramos
                continue
            
            # for each component in the tramo, place it with the given gap and calculate the depth of the pipe representation based on the component length and gap, then create the pipe representation for the tramo with the calculated depth
            for i, component in enumerate(components):                
                st.write(f'Processing Component #{component.id()} - {component.Name}...')
                component_type = element.get_type(component)

                if f'{old_component}-{getattr(component, "ObjectType", None)}' in dists:
                    dist_component = dists[f'{old_component}-{getattr(component, "ObjectType", None)}']  
                    st.write(f'Component {component.id()} - {component.Name} has specific gap defined for transition from {old_component} to {getattr(component, "ObjectType", "Unknown")}, using dist={dist_component} m')                  
                else:
                    dist_component = dist
                    st.write(f'Component {component.id()} - {component.Name} has no specific gap defined for its type {getattr(component, "ObjectType", "Unknown")}, using default dist={dist_component} m')
                
                # get component length from geometry, if not possible, use tramo gap as default
                tam = get_component_length(component)
                if tam is None:
                    tam = dist_component

                if i == 0:
                    first_tam = tam
                else:
                    x += dist_component
                
                if getattr(component, 'ObjectType', None) == 'PipePullingHead':
                    pullings.append(component)
                    continue
                # if getattr(component, 'ObjectType', None) == 'PipePullingHead':
                #     y = -dist
                #     tam = 0
                # else:
                #     y = 0

                

                matrix = np.eye(4)
                if i + 1 > n / 2:
                    matrix = placement.rotation(180, "Z") @ matrix
                    x += tam
                matrix[:3, 3] = (x, y, 0)

                geometry.edit_object_placement(model, product=component, matrix=matrix, is_si=True)
                st.write(f':blue[Component {component.id()} - {component.Name} ({getattr(component, "ObjectType", "Unknown")}) placed at x={x:.3f}]')

                # process subcomponents if exist (e.g. accessories f or fittings with ports)
                # subcomponents = get_connected(component)
                # if len(subcomponents) > 0:
                #     st.write(f'Component {component.id()} - {component.Name} has {len(subcomponents)} subcomponents, processing placements...')
                #     for sub in subcomponents:
                #         st.write(f'Processing Subcomponent #{sub.id()} - {sub.Name}...')
                #         # sub_matrix = np.eye(4)
                #         # sub_matrix[:3, 3] = (x, y - dist, 0)
                #         # geometry.edit_object_placement(model, product=sub, matrix=sub_matrix, is_si=True)                        
                #         nest.assign_object(model, related_objects=[sub], relating_object=tramo)
                #         st.write(f':cyan[Subcomponent {sub.id()} - {sub.Name} placed at x={x:.3f}]')
                # else:
                #     st.write(f'Component {component.id()} - {component.Name} has no subcomponents.')
                
                depth = x - x_start - 2 * tam
                #x += tam + dist
                old_x = x
                if i + 1 <= n / 2:
                    x += tam
                old_component = component.ObjectType

            x += dist_tramos # - tam
            create_pipe(model, tramo, (x_start + first_tam, 0), depth)

            # place pullings at the start and end of the tramo if exist
            if len(pullings) > 0:
                start_pulling = pullings[0]
                matrix = np.eye(4)
                matrix[:3, 3] = (x_start+first_tam, -dist , 0)
                geometry.edit_object_placement(model, product=start_pulling, matrix=matrix, is_si=True)
                st.write(f':magenta[Pulling {start_pulling.id()} - {start_pulling.Name} placed at x={x_start + first_tam:.3f}]')
            
            if len(pullings) > 1:
                end_pulling = pullings[1]
                matrix = np.eye(4)
                matrix = placement.rotation(180, "Z") @ matrix
                matrix[:3, 3] = (x_start + first_tam + depth, -dist , 0)
                geometry.edit_object_placement(model, product=end_pulling, matrix=matrix, is_si=True)
                st.write(f':magenta[Pulling {end_pulling.id()} - {end_pulling.Name} placed at x={x_start + first_tam + depth:.3f}]')

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
        page_icon="💣",
        layout="wide",
    )

    st.title("Unifilar3D — IFC Unifilar Representation Generator (26.05.03)")

    # ── Session state ───────────────────────────────────────────────────────
    if "output_bytes" not in st.session_state:
        st.session_state.output_bytes = None
    if "output_name" not in st.session_state:
        st.session_state.output_name = "model_clone.ifc"

    # ── Sidebar: configuration ──────────────────────────────────────────────
    with st.sidebar:
        st.header("Configuration")

        model_file   = st.file_uploader("Input Model (.ifc)", type=["ifc"], key="model_file")
        catalog_file = st.file_uploader("IFC Catalog (.ifc)", type=["ifc"], key="catalog_file")

        st.divider()

        output_name  = st.text_input("Output filename", "model_clone.ifc")
        attribute    = st.text_input("Attribute to check for gap (e.g. 'Name' or 'ElementType')", "ElementType")
        dist         = st.number_input("Component gap — dist (m)", value=DEFAULT_DIST,        min_value=0.0, step=0.05, format="%.3f")
        dist_tramos  = st.number_input("Tramo gap — dist_tramos (m)", value=DEFAULT_DIST_TRAMOS, min_value=0.0, step=0.01, format="%.3f")
        st.divider()
        execute = st.button("▶ Execute", type="primary", use_container_width=True)
        if st.session_state.output_bytes is not None:
            if st.button("🗑 Limpar mensagens", use_container_width=True):
                st.session_state.output_bytes = None
                st.session_state.output_name = "model_clone.ifc"
                st.rerun()

    # ── Main area ───────────────────────────────────────────────────────────
    if not execute:
        if st.session_state.output_bytes is None:
            st.info("Upload the input model and catalog in the sidebar, adjust parameters, then click **Execute**.")
        else:
            st.download_button(
                label="⬇ Download output IFC",
                data=st.session_state.output_bytes,
                file_name=st.session_state.output_name,
                mime="application/octet-stream",
            )
        return

    if model_file is None or catalog_file is None:
        st.error("Please upload both the **Input Model** and the **IFC Catalog** before executing.")
        return

    # Download button placeholder at the top
    download_placeholder = st.empty()

    output_bytes = None

    # Messages / progress container below
    with st.container(border=True):
        with tempfile.TemporaryDirectory() as tmpdir:
            model_path   = os.path.join(tmpdir, model_file.name)
            catalog_path = os.path.join(tmpdir, catalog_file.name)

            with open(model_path, "wb") as f:
                f.write(model_file.read())
            with open(catalog_path, "wb") as f:
                f.write(catalog_file.read())

            progress_bar = st.progress(0, text="Starting...")
            status_text  = st.empty()

            try:
                with st.spinner("Processing IFC model…"):
                    output_bytes = run_processing(
                        model_path, catalog_path,
                        attribute, dist, dist_tramos,
                        progress_bar, status_text,
                    )
                progress_bar.progress(1.0, text="Done!")
                status_text.text("Processing complete.")
                st.success("Model processed successfully!")
            except Exception as exc:
                st.error(f"Processing failed: {exc}")

    # Populate download button at the top once processing is done
    if output_bytes is not None:
        st.session_state.output_bytes = output_bytes
        st.session_state.output_name = output_name
        download_placeholder.download_button(
            label="⬇ Download output IFC",
            data=output_bytes,
            file_name=output_name,
            mime="application/octet-stream",
        )


if __name__ == "__main__":
    main()

