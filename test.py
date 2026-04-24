import ifcopenshell
from ifcopenshell.util import representation, element
from ifcopenshell.api import type, geometry, context, style, material

catalog = ifcopenshell.open("catalog.ifc")
t = catalog.by_id(7266)
print(t)
mat = element.get_material(t)
print(mat)
sub_context = representation.get_context(catalog, 'Model', 'Body', 'MODEL_VIEW')  
print(sub_context)
representation_style = representation.get_material_style(mat, sub_context)
print(representation_style)