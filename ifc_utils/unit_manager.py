import ifcopenshell
import ifcopenshell.api
import ifcopenshell.api.unit
import os
import json

'''

    Cria unidades IFC a partir de símbolos de unidades comuns, verificando se já existem no modelo antes de criar 
    novas instâncias. A classe UnitManager contém um dicionário de unidades comuns e seus correspondentes tipos e
    classes IFC.

        UnitManager.metadata -> contém informações adicionais sobre as propriedades, incluindo a unidade associada a cada propriedade,
        o que permite atribuir unidades corretas às propriedades do modelo com base em um mapeamento pré-definido.

        UnitManager.units -> dicionário que mapeia símbolos de unidades comuns para seus tipos, classes e atributos correspondentes no IFC.

        UnitManager.get_project_units -> método auxiliar para verificar se uma unidade com o mesmo tipo e prefixo já existe no modelo,
        retornando a unidade existente se encontrada.

        UnitManager.create_unit -> método principal para criar unidades no modelo, verificando primeiro se a unidade já existe e, se não existir,
        criando uma nova instância com base na classe IFC apropriada (IfcSIUnit, IfcDerivedUnit, IfcConversionBasedUnit ou IfcContextDependentUnit)
        e atribuindo os atributos necessários.

'''
class UnitManager:
    def __init__(self, base_path=None):
        self.base_path = base_path or os.path.dirname(os.path.realpath(__file__))
        self.units = self._load_json('units.json')
        self.properties = self._load_json('properties.json')

    def _load_json(self, filename):
        file_path = os.path.join(self.base_path, filename)
        with open(file_path, 'r', encoding='utf-8') as file:
            return json.load(file)

    @staticmethod
    def get_project_units(model, unit_type, prefix=None):
        project_units = model.by_type('IfcNamedUnit') + model.by_type('IfcDerivedUnit')
        for unit in project_units:
            if unit.UnitType == unit_type and getattr(unit, 'Prefix', None) == prefix:
                return unit
        return None  # Retorna None se a unidade não for encontrada
   
    def create_unit(self, model, symbol_unit):
        units = self.units
        if symbol_unit in units:
            unit_type = ifcopenshell.util.unit.get_measure_unit_type(units[symbol_unit]['ifc_attribute'])
            prefix = units[symbol_unit]['prefix'] if 'prefix' in units[symbol_unit] else None
            units_loaded = self.get_project_units(model, unit_type, prefix)

            if units_loaded:
                return units_loaded  # Retorna a unidade existente se já estiver presente
            
            if units[symbol_unit]['ifc_class'] == 'IfcSIUnit':                                    
                ifc_unit = ifcopenshell.api.unit.add_si_unit(
                    model,
                    unit_type=unit_type,
                    prefix=prefix
                )
            
            elif units[symbol_unit]['ifc_class'] == 'IfcDerivedUnit':
                attributes = {}
                for base_unit in units[symbol_unit]['compose']:                    
                    if base_unit in units:
                        ifc_base_unit = self.create_unit(model, base_unit)
                        attributes[ifc_base_unit] = units[symbol_unit]['compose'][base_unit]
                    else:
                        return None  # Base unit not found in units dictionary
                ifc_unit = ifcopenshell.api.unit.add_derived_unit(model, userdefinedtype=None, unit_type=unit_type, attributes=attributes)
            
            elif units[symbol_unit]['ifc_class'] == 'IfcConversionBasedUnit':
                ifc_unit = ifcopenshell.api.unit.add_conversion_based_unit(model, name=units[symbol_unit]['ifc_value'])

            elif units[symbol_unit]['ifc_class'] == 'IfcContextDependentUnit':
                ifc_unit = ifcopenshell.api.unit.add_context_dependent_unit(model, name=units[symbol_unit]['ifc_value'])
            
            else:
                return None  # Unsupported unit class
            
            return ifc_unit

        return None
        


