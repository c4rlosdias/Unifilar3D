import bpy
import os
import pandas as pd
import ifcopenshell
import ifcopenshell.api
from .ifc_utils.unit_manager import *
from .ifc_utils import unit_manager
import logging

logger = logging.getLogger("manage_tools_addon")

def update_predefined_types():
    model = tool.Ifc.get()
    for entity in model.by_type('IfcElement'):
        if entity.IsTypedBy:
            type = entity.IsTypedBy[0].RelatingType
            if type.ElementType:
                object_type = type.ElementType.replace("Type", "")
                object_type = type.ElementType.replace("Structure", "Segment")
                entity.ObjectType = object_type
                entity.PredefinedType = None  # Limpa o PredefinedType para forçar a atualização na UI
    
def get_property_info():
    prop_units = {}
    metadata_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'resources', 'metadata.json')
    if os.path.exists(metadata_path):
        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        for classe, attribs in metadata.items():
            for pset, props in attribs.get('properties', {}).items():
                for prop in props:
                    prop_units[prop['code']] = {
                        'unit': prop.get('unit', None),
                        'description': prop.get('description', None)
                    }
        return prop_units
    else:
        return None
  



##########################################################################################################    
##  Properties
###########################################################################################################
  

class Operator_load_metadata(bpy.types.Operator):
    """Carrega metadata.json e popula object_types"""
    bl_idname  = "pset.load_metadata"
    bl_label   = "Load Metadata"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        if unit_manager.load_metadata_file():
            unit_manager.populate_object_types()
            self.report({'INFO'}, f"Metadata carregado com {len(unit_manager.metadata)} classes.")
        else:
            self.report({'WARNING'}, "metadata.json não encontrado ou vazio.")
        return {'FINISHED'}


class Operator_load_bsdd(bpy.types.Operator):
    """"""
    bl_idname  = "pset.load_bsdd"
    bl_label   = "Load bsdd"
    bl_options = {"REGISTER", "UNDO"} 

   
    def execute(self, context):
        props = context.scene.pset_props
        props.properties.clear()
        uri = props.uri
        context.window.cursor_set('WAIT')
        try:
            data_instance = unit_manager.Data()
            print(f"Loading bSDD from {uri}...")
            logger.info(f"Loading bSDD from {uri}")
            result = data_instance.load_from_bsdd(uri)
            if result != 'Done':
                logger.error(f"Failed to load bSDD from {uri}: {result}")
                self.report({'ERROR'}, f"Failed to load bsdd: {result}")
                return {'CANCELLED'}

            metadata_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'resources', 'metadata.json')
            print(f"Saving metadata to {metadata_path}...")
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(unit_manager.metadata, f, indent=4, ensure_ascii=False)
            logger.info(f"bSDD loaded from {uri}, metadata updated.")
            self.report({'INFO'}, "bSDD carregado com sucesso.")
        except Exception as e:
            logger.error(f"Failed to load bSDD from {uri}: {e}")
            self.report({'ERROR'}, f"Failed to load bsdd: {e}")
            return {'CANCELLED'}
        finally:
            context.window.cursor_set('DEFAULT')

        return {"FINISHED"}
       
class Operator_add_pset(bpy.types.Operator):
    """"""
    bl_idname  = "pset.add_pset"
    bl_label   = "Add Pset to IFC"
    bl_options = {"REGISTER", "UNDO"} 

    def execute(self, context):   
        try:
            template = PropTempl.template            
            if template is None:
                PropTempl.get_template()
                template = PropTempl.template

            res = PropTempl.add_pset_template(unit_manager.metadata)
            if not res:
                self.report({'ERROR'}, "Failed to add Pset template.")
                return {'CANCELLED'}
            
            print("Pset template added successfully.")
            print("Template file path:", PropTempl.filepath)
            logger.info("Pset template added successfully.")
            logger.info(f"Template file path: {PropTempl.filepath}")

        except Exception as e:
            logger.error(f"Failed to add Pset template: {e}")
            self.report({'ERROR'}, f"Failed to add Pset template: {e}")
            return {'CANCELLED'}
        
        return {"FINISHED"}


class Operator_fix_units(bpy.types.Operator):
    """"""
    bl_idname  = "pset.fix_units"
    bl_label   = "Fix Units"
    bl_options = {"REGISTER", "UNDO"} 

    def execute(self, context):   
        try:
            data_instance = unit_manager.UnitManager()
            model = tool.Ifc.get()
            properties = model.by_type('IfcProperty')
            prop_info = get_property_info()
            if prop_info is None:
                self.report({'ERROR'}, "Property metadata not found. Please load bSDD first.")
                logger.error("Property metadata not found. Please load bSDD first.")
                return {'CANCELLED'}
            
            print(prop_info)
            n=0
            for prop in properties:

                if prop.Name in prop_info and 'description' in prop_info[prop.Name]:
                    prop.Description = prop_info[prop.Name]['description']
                else:
                    prop.Description = ""

                if prop.is_a("IfcPropertySingleValue"):
                    if not prop.Unit:
                        unit_info = prop_info[prop.Name] if prop.Name in prop_info else None
                        if unit_info and 'unit' in unit_info:
                            unit = data_instance.create_unit(model, unit_info['unit'])
                            prop.Unit = unit
                            n += 1


            self.report({'INFO'}, f"{len(properties)} properties processed and {n} units fixed successfully.")
            logger.info(f"{len(properties)} properties processed and {n} units fixed successfully.")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to fix units: {e}")
            logger.error(f"Failed to fix units: {e}")
            return {'CANCELLED'}
        
#############################################################################################################
## Predefined Types
##############################################################################################################

class Operator_update_predefined_type(bpy.types.Operator):
    """"""
    bl_idname  = "pset.upt_predefined_types"
    bl_label   = "Update Predefined Types"
    bl_options = {"REGISTER", "UNDO"} 

    def execute(self, context):   
        try:
            update_predefined_types()
            self.report({'INFO'}, "Predefined types updated successfully.")
            logger.info("Predefined types updated successfully.")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to update predefined types: {e}")
            logger.error(f"Failed to update predefined types: {e}")
            return {'CANCELLED'}