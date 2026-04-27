import ifcopenshell
from ifcopenshell import geom
from ifcopenshell.util import representation, element, selector, placement, shape
from ifcopenshell.api import type, geometry, context, style, material
import numpy as np
import logging
from pathlib import Path
from tqdm import tqdm

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
        
    
def add_catalog_representation(type_target : ifcopenshell.entity_instance, model : ifcopenshell.file) -> list:
    """
    Clone the representation map of the given type target.
    """
    sub_context = representation.get_context(model, 'Model', 'Body', 'MODEL_VIEW')  
    if sub_context is None:
        sub_context = context.add_context(model, context_type='Model', context_identifier='Body')
    catalog = ifcopenshell.open(CATALOG_INPUT)

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


def prompt(label: str, default: str) -> str:
    value = input(f"  {label} [{default}]: ").strip()
    return value if value else default


def print_header():
    print(r"""
  ██╗   ██╗███╗   ██╗██╗███████╗██╗██╗      █████╗ ██████╗ ██████╗ ██████╗ 
  ██║   ██║████╗  ██║██║██╔════╝██║██║     ██╔══██╗██╔══██╗╚════██╗██╔══██╗
  ██║   ██║██╔██╗ ██║██║█████╗  ██║██║     ███████║██████╔╝ █████╔╝██║  ██║
  ██║   ██║██║╚██╗██║██║██╔══╝  ██║██║     ██╔══██║██╔══██╗ ╚═══██╗██║  ██║
  ╚██████╔╝██║ ╚████║██║██║     ██║███████╗██║  ██║██║  ██║██████╔╝██████╔╝
   ╚═════╝ ╚═╝  ╚═══╝╚═╝╚═╝     ╚═╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝╚═════╝ 
              IFC Unifilar Representation Generator
    """)


def print_config(model_input, catalog_input, model_output, log_file, verbose, dist, dist_tramos):
    print("\n  Current configuration:")
    print(f"    [1] Input model       : {model_input}")
    print(f"    [2] IFC catalog       : {catalog_input}")
    print(f"    [3] Output model      : {model_output}")
    print(f"    [4] Log file          : {log_file}")
    print(f"    [5] Verbose           : {'yes' if verbose else 'no'}")
    print(f"    [6] Component gap (dist)        : {dist} m")
    print(f"    [7] Tramo gap (dist_tramos)      : {dist_tramos} m")


def main():
    model_input   = DEFAULT_MODEL_INPUT
    catalog_input = DEFAULT_CATALOG_INPUT
    model_output  = DEFAULT_MODEL_OUTPUT
    log_file      = DEFAULT_LOG_FILE
    verbose       = False
    dist          = DEFAULT_DIST
    dist_tramos   = DEFAULT_DIST_TRAMOS

    while True:
        print_header()
        print_config(model_input, catalog_input, model_output, log_file, verbose, dist, dist_tramos)
        print()
        print("  [E] Execute")
        print("  [Q] Quit")
        print()

        choice = input("  Option: ").strip().upper()

        if choice == "Q":
            print("\n  Exiting.\n")
            break
        elif choice == "E":
            print()
            break
        elif choice == "1":
            model_input   = prompt("Input model",  model_input)
        elif choice == "2":
            catalog_input = prompt("IFC catalog",  catalog_input)
        elif choice == "3":
            model_output  = prompt("Output model", model_output)
        elif choice == "4":
            log_file      = prompt("Log file",     log_file)
        elif choice == "5":
            verbose = not verbose
            print(f"  Verbose: {'enabled' if verbose else 'disabled'}")
        elif choice == "6":
            value = prompt("Component gap (dist) [m]", str(dist))
            try:
                dist = float(value)
            except ValueError:
                print("  Invalid value. Please enter a decimal number.")
        elif choice == "7":
            value = prompt("Tramo gap (dist_tramos) [m]", str(dist_tramos))
            try:
                dist_tramos = float(value)
            except ValueError:
                print("  Invalid value. Please enter a decimal number.")
        else:
            print("  Invalid option.\n")
        print()

    if choice == "Q":
        return

    handlers = [logging.FileHandler(log_file, encoding="utf-8")]
    if verbose:
        handlers.append(logging.StreamHandler())
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=handlers,
    )

    # make catalog path available to add_catalog_representation
    global CATALOG_INPUT
    CATALOG_INPUT = catalog_input

    model = ifcopenshell.open(model_input)
    print(f'Model "{model_input}" opened successfully!')
    settings = geom.settings()

    # get types' representation map from catalog and assign to the model
    types = model.by_type('IfcPipeFittingType') + model.by_type('IfcPipeSegmentType')
    logging.info('Iniciating processing of types representation map from catalog...')
    for type_target in tqdm(types, desc='Processing Types    ', unit='type', total=len(types)):
        logging.debug(f'Processing Type {type_target.id()} - {type_target.Name}...')
        if add_catalog_representation(type_target, model):
            instances = element.get_types(type_target)
            for instance in instances:
                geometry.edit_object_placement(model, product=instance)
            type.unassign_type(model, related_objects=list(instances))
            type.assign_type(model, related_objects=list(instances), relating_type=type_target)
        else:
            logging.debug(f'Type {type_target.Name} not found in catalog!')

    # create tramos
    buildings = model.by_type('IfcBuilding')
    for building in tqdm(buildings, desc='Processing Buildings', unit='building', total=len(buildings)):
        if building.ObjectType != 'SubseaPipeline':
            continue

        # dist and dist_tramos are configured via the interactive menu

        logging.info(f'Processing Building {building.id()} - {building.Name}...')

        x = 0        # running X position across all tramos in this building
        x_start = 0  # X at the start of the current tramo
        y = 0
        ###########################################################################################################
        ###########################################################################################################
        for tramo in element.get_contained(building): # or get_components depending on how the model is structured
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
                if i+1 > n / 2:
                    matrix = placement.rotation(180, "Z") @ matrix
                    x += tam

                matrix[:3, 3] = (x, y, 0)
                geometry.edit_object_placement(model, product=component, matrix=matrix, is_si=True)
                logging.info(f'Component {component.id()} - {component.Name} ({component_type.ElementType}) placed at x={x:.3f}')

                depth = x - x_start - 2 * tam
                x += tam + dist

            # adjust x back after the last component
            x += dist_tramos - (tam + dist)  
            
            create_pipe(model, tramo, (x_start + first_tam, y), depth)

    Path(model_output).parent.mkdir(parents=True, exist_ok=True)
    model.write('.'.join(model_input.split('.')[:-1]) + '_clone.ifc')
    print(f'Model written to "{'.'.join(model_input.split('.')[:-1]) + '_clone.ifc'}" successfully!')


if __name__ == "__main__":
    main()



    
