# Referência Completa: ifcopenshell.api (v0.8.5)

Extraído da documentação oficial: https://docs.ifcopenshell.org/autoapi/ifcopenshell/api/index.html

## Como chamar a API

```python
import ifcopenshell
import ifcopenshell.api

# Estilo moderno (recomendado 0.8+) — chamada direta ao módulo
parede = ifcopenshell.api.root.create_entity(model, ifc_class='IfcWall', name='P01')

# Estilo legado (ainda funciona) — string dispatcher
parede = ifcopenshell.api.run('root.create_entity', model, ifc_class='IfcWall', name='P01')
```

O primeiro argumento é sempre o `ifcopenshell.file` (normalmente chamado de `model`).

---

## Índice de Módulos

| Módulo | Finalidade |
|--------|-----------|
| `root` | Criar, copiar, reclassificar, remover qualquer produto IFC |
| `attribute` | Editar atributos de entidades |
| `pset` | Property sets e Quantity sets |
| `spatial` | Containment — vincular elementos a pavimentos/espaços |
| `aggregate` | Decomposição — Project > Site > Building > Storey |
| `nest` | Relações de nesting (componentes dentro de elementos) |
| `context` | Contextos geométricos de representação |
| `unit` | Unidades do projeto |
| `type` | Tipos de elementos (IfcWallType, etc.) |
| `material` | Materiais simples, sets em camadas/perfis/constituintes |
| `geometry` | Representações geométricas e placements |
| `georeference` | Georreferenciamento CRS |
| `owner` | Pessoas, organizações, aplicações, papéis |
| `classification` | Classificações (Uniclass, Omniclass, SINAPI, etc.) |
| `group` | Grupos de elementos |
| `layer` | Camadas (layers) de apresentação |
| `style` | Estilos de apresentação (cores, texturas) |
| `profile` | Perfis de seção transversal (IPE, HEA, arbitrários) |
| `feature` | Aberturas e preenchimentos (portas/janelas em paredes) |
| `boundary` | Space boundaries (relações espaço-elemento) |
| `system` | Sistemas MEP e conexões de portas |
| `document` | Documentos e referências externas |
| `constraint` | Objetivos e métricas (requisitos de informação) |
| `sequence` | Cronograma 4D |
| `cost` | Orçamento 5D |
| `resource` | Recursos (mão de obra, materiais, equipamentos) |
| `grid` | Grids de projeto |
| `library` | Bibliotecas de ativos e referências |
| `project` | Operações de projeto (append, declaração) |
| `pset_template` | Templates de property sets customizados |
| `structural` | Análise estrutural |
| `alignment` | Alinhamentos para infraestrutura linear (IFC4X3) |
| `cogo` | Coordinate geometry — pontos de levantamento |
| `drawing` | Anotações e textos em plantas/cortes |

---

## root — Criar e gerenciar produtos

**Funções:** `create_entity`, `copy_class`, `reassign_class`, `remove_product`

```python
# Criar qualquer entidade IFC raiz
entidade = ifcopenshell.api.root.create_entity(
    model,
    ifc_class='IfcWall',
    predefined_type=None,   # 'SOLIDWALL', 'USERDEFINED', etc.
    name=None
)

# Remover produto e todos os relacionamentos
ifcopenshell.api.root.remove_product(model, product=parede)

# Copiar produto (novo GlobalId)
copia = ifcopenshell.api.root.copy_class(model, product=parede)

# Reclassificar para outra classe IFC (NOVO em 0.8.x)
ifcopenshell.api.root.reassign_class(
    model,
    product=elemento,
    ifc_class='IfcPipeSegment',
    predefined_type='RIGIDSEGMENT'
)
```

---

## attribute — Editar atributos

**Funções:** `edit_attributes`

```python
ifcopenshell.api.attribute.edit_attributes(
    model,
    product=elemento,
    attributes={
        'Name': 'Novo Nome',
        'Description': 'Descrição atualizada',
        'ObjectType': 'USERDEFINED_TYPE',
        'Tag': 'TAG-001'
    }
)
```

---

## pset — Property Sets e Quantity Sets

**Funções:** `add_pset`, `add_qto`, `assign_pset`, `edit_pset`, `edit_qto`, `remove_pset`, `unassign_pset`, `unshare_pset`

```python
# Criar Pset e adicionar propriedades
pset = ifcopenshell.api.pset.add_pset(model, product=elemento, name='Pset_WallCommon')
ifcopenshell.api.pset.edit_pset(
    model,
    pset=pset,
    properties={
        'IsExternal': True,
        'FireRating': 'REI60',
        'LoadBearing': False,
        'ThermalTransmittance': 0.35
    }
)

# Criar Qto e adicionar quantidades
qto = ifcopenshell.api.pset.add_qto(model, product=elemento, name='Qto_WallBaseQuantities')
ifcopenshell.api.pset.edit_qto(
    model,
    qto=qto,
    properties={
        'Length': 3.5,    # IfcQuantityLength
        'Area': 10.5,     # IfcQuantityArea
        'Volume': 2.625   # IfcQuantityVolume
    }
)

# Compartilhar Pset entre múltiplos elementos
ifcopenshell.api.pset.assign_pset(model, products=[el1, el2], pset=pset)
ifcopenshell.api.pset.unassign_pset(model, products=[elemento], pset=pset)

# Converter Pset compartilhado em exclusivo (NOVO em 0.8.5)
ifcopenshell.api.pset.unshare_pset(model, pset=pset, product=elemento)

ifcopenshell.api.pset.remove_pset(model, pset=pset)
```

---

## spatial — Containment espacial

**Funções:** `assign_container`, `unassign_container`, `reference_structure`, `dereference_structure`

```python
# Vincular elemento a pavimento (IfcRelContainedInSpatialStructure)
ifcopenshell.api.spatial.assign_container(
    model,
    products=[parede, laje, porta],
    relating_structure=pavimento
)
ifcopenshell.api.spatial.unassign_container(model, products=[parede])

# Referência (elemento em múltiplos pavimentos, sem containment exclusivo)
ifcopenshell.api.spatial.reference_structure(
    model, products=[escada], relating_structure=pavimento2
)
ifcopenshell.api.spatial.dereference_structure(
    model, products=[escada], relating_structure=pavimento2
)
```

---

## aggregate — Decomposição hierárquica

**Funções:** `assign_object`, `unassign_object`

```python
# Criar hierarquia Project > Site > Building > Storey (IfcRelAggregates)
ifcopenshell.api.aggregate.assign_object(
    model,
    products=[pavimento],
    relating_object=edificio
)
ifcopenshell.api.aggregate.unassign_object(model, products=[pavimento])
```

---

## nest — Nesting de componentes

**Funções:** `assign_object`, `unassign_object`, `change_nest`, `reorder_nesting`

```python
ifcopenshell.api.nest.assign_object(model, products=[componente], relating_object=host)
ifcopenshell.api.nest.change_nest(model, product=componente, new_nest=novo_host)
ifcopenshell.api.nest.reorder_nesting(model, item=componente, new_index=0)
ifcopenshell.api.nest.unassign_object(model, products=[componente])
```

---

## context — Contextos geométricos

**Funções:** `add_context`, `edit_context`, `remove_context`

```python
ctx_model = ifcopenshell.api.context.add_context(model, context_type='Model')
body = ifcopenshell.api.context.add_context(
    model,
    context_type='Model',
    context_identifier='Body',
    target_view='MODEL_VIEW',
    parent=ctx_model
)
# context_identifier comuns: 'Body', 'Axis', 'Box', 'FootPrint', 'Profile', 'SurveyPoints'
# target_view: 'MODEL_VIEW', 'PLAN_VIEW', 'ELEVATION_VIEW', 'SECTION_VIEW', 'SKETCH_VIEW'

ctx_plan = ifcopenshell.api.context.add_context(model, context_type='Plan')
ifcopenshell.api.context.remove_context(model, context=body)
```

---

## unit — Unidades

**Funções:** `assign_unit`, `add_si_unit`, `add_conversion_based_unit`, `add_derived_unit`, `add_context_dependent_unit`, `add_monetary_unit`, `edit_named_unit`, `edit_derived_unit`, `edit_monetary_unit`, `remove_unit`, `unassign_unit`

```python
# Padrão SI (metros)
ifcopenshell.api.unit.assign_unit(model)

# Milímetros
mm = ifcopenshell.api.unit.add_si_unit(model, unit_type='LENGTHUNIT', prefix='MILLI')
ifcopenshell.api.unit.assign_unit(model, units=[mm])

# Baseado em conversão (pés, polegadas)
ft = ifcopenshell.api.unit.add_conversion_based_unit(model, name='foot', unit_type='LENGTHUNIT')

# Tipos suportados: LENGTHUNIT, AREAUNIT, VOLUMEUNIT, PLANEANGLEUNIT,
#                  MASSUNIT, TIMEUNIT, THERMODYNAMICTEMPERATUREUNIT, PRESSUREUNIT
# Prefixos SI: MILLI, CENTI, DECI, HECTO, KILO, MEGA
```

---

## type — Tipos de elementos

**Funções:** `assign_type`, `unassign_type`, `map_type_representations`

```python
tipo = ifcopenshell.api.root.create_entity(model, ifc_class='IfcWallType', name='W-200mm')
ifcopenshell.api.type.assign_type(
    model,
    related_objects=[parede1, parede2],
    relating_type=tipo
)
ifcopenshell.api.type.unassign_type(model, related_objects=[parede1])
# Propagar geometria do tipo para as instâncias
ifcopenshell.api.type.map_type_representations(model, related_object=parede1, relating_type=tipo)
```

---

## material — Materiais

**Funções:** `add_material`, `edit_material`, `remove_material`, `assign_material`, `unassign_material`, `copy_material`, `add_material_set`, `remove_material_set`, `add_layer`, `edit_layer`, `edit_layer_usage`, `remove_layer`, `add_constituent`, `edit_constituent`, `remove_constituent`, `set_shape_aspect_constituents`, `add_list_item`, `remove_list_item`, `add_profile`, `edit_profile`, `edit_profile_usage`, `assign_profile`, `remove_profile`, `reorder_set_item`

```python
# Material simples
mat = ifcopenshell.api.material.add_material(model, name='Concreto', category='concrete')
ifcopenshell.api.material.assign_material(model, products=[laje], type='IfcMaterial', material=mat)

# Material em camadas (paredes multicamada)
set_camadas = ifcopenshell.api.material.add_material_set(
    model, name='Parede Multicamada', set_type='IfcMaterialLayerSet'
)
cam = ifcopenshell.api.material.add_layer(model, layer_set=set_camadas, material=reboco)
ifcopenshell.api.material.edit_layer(model, layer=cam, attributes={'LayerThickness': 0.02})
ifcopenshell.api.material.assign_material(
    model, products=[parede], type='IfcMaterialLayerSetUsage', material=set_camadas
)

# set_type options: 'IfcMaterialLayerSet', 'IfcMaterialConstituentSet', 'IfcMaterialProfileSet', 'IfcMaterialList'
```

---

## geometry — Representações geométricas

**Funções:** `add_representation`, `assign_representation`, `unassign_representation`, `remove_representation`, `copy_representation`, `map_representation`, `edit_object_placement`, `add_mesh_representation`, `add_profile_representation`, `add_axis_representation`, `add_footprint_representation`, `add_boolean`, `remove_boolean`, `add_shape_aspect`, `clip_solid`, `clip_solid_bounded`, `connect_element`, `connect_path`, `connect_wall`, `disconnect_element`, `disconnect_path`, `create_2pt_wall`, `add_door_representation`, `add_window_representation`, `add_wall_representation`, `add_slab_representation`, `add_railing_representation`, `add_topology_representation`, `regenerate_wall_representation`, `validate_type`

```python
# Placement (matriz 4x4 homogênea)
import numpy as np
ifcopenshell.api.geometry.edit_object_placement(
    model, product=elemento, matrix=np.eye(4)
)

# Representação por malha
rep = ifcopenshell.api.geometry.add_mesh_representation(
    model, context=body,
    vertices=[(0,0,0), (1,0,0), (1,1,0), (0,1,0)],
    faces=[(0,1,2,3)]
)
ifcopenshell.api.geometry.assign_representation(model, product=elemento, representation=rep)

# Extrusão de perfil
rep = ifcopenshell.api.geometry.add_profile_representation(
    model, context=body, profile=perfil, depth=3.0
)

# Conectar elementos (IfcRelConnectsElements)
ifcopenshell.api.geometry.connect_element(
    model, relating_element=viga, related_element=coluna
)

# Booleana (subtração)
ifcopenshell.api.geometry.add_boolean(
    model, representation=rep_host, operator='DIFFERENCE', representation2=rep_void
)

ifcopenshell.api.geometry.remove_representation(model, representation=rep)
```

---

## owner — Pessoas, organizações, aplicações

**Funções:** `add_person`, `edit_person`, `remove_person`, `add_organisation`, `edit_organisation`, `remove_organisation`, `add_person_and_organisation`, `remove_person_and_organisation`, `add_application`, `edit_application`, `remove_application`, `add_role`, `edit_role`, `remove_role`, `add_address`, `edit_address`, `remove_address`, `add_actor`, `edit_actor`, `remove_actor`, `assign_actor`, `unassign_actor`, `settings`, `create_owner_history`, `update_owner_history`

```python
# Configurar owner (obrigatório para OwnerHistory)
ifcopenshell.api.owner.settings.set_user(lambda: person_and_org)
ifcopenshell.api.owner.settings.set_application(lambda: application)

pessoa = ifcopenshell.api.owner.add_person(
    model, identification='jsilva', family_name='Silva', given_name='João'
)
org = ifcopenshell.api.owner.add_organisation(
    model, identification='PETROBRAS', name='Petróleo Brasileiro S.A.'
)
p_and_o = ifcopenshell.api.owner.add_person_and_organisation(model, person=pessoa, organisation=org)
app = ifcopenshell.api.owner.add_application(
    model,
    application_developer=org,
    version='1.0',
    application_full_name='ifc2e3d Pipeline',
    application_identifier='IFC2E3D'
)
```

---

## classification — Sistemas de classificação

**Funções:** `add_classification`, `edit_classification`, `remove_classification`, `add_reference`, `edit_reference`, `remove_reference`

```python
classif = ifcopenshell.api.classification.add_classification(model, classification='SINAPI')
ifcopenshell.api.classification.edit_classification(
    model, classification=classif,
    attributes={
        'Name': 'SINAPI',
        'Edition': '2024',
        'Source': 'CAIXA/CEF',
        'Location': 'https://sinapi.caixa.gov.br'
    }
)
ref = ifcopenshell.api.classification.add_reference(
    model,
    product=elemento,
    identification='72013',
    name='CONCRETO FCK=25MPA',
    classification=classif
)
```

---

## group — Grupos

**Funções:** `add_group`, `edit_group`, `assign_group`, `unassign_group`, `remove_group`, `update_group_products`

```python
grupo = ifcopenshell.api.group.add_group(model, name='Estrutura Bloco A', ifc_class='IfcGroup')
ifcopenshell.api.group.assign_group(model, products=[v1, v2, c1], group=grupo)
ifcopenshell.api.group.unassign_group(model, products=[v1], group=grupo)
ifcopenshell.api.group.update_group_products(model, group=grupo, products=[c1, c2, c3])
ifcopenshell.api.group.remove_group(model, group=grupo)
```

---

## layer — Camadas de apresentação

**Funções:** `add_layer`, `add_layer_with_style`, `edit_layer`, `assign_layer`, `unassign_layer`, `remove_layer`

```python
layer = ifcopenshell.api.layer.add_layer(model, name='S-WALL-FULL')
ifcopenshell.api.layer.edit_layer(model, layer=layer, attributes={'Description': 'Paredes'})
ifcopenshell.api.layer.assign_layer(model, items=[rep], layer=layer)
ifcopenshell.api.layer.remove_layer(model, layer=layer)
```

---

## style — Estilos visuais

**Funções:** `add_style`, `add_surface_style`, `add_surface_textures`, `assign_item_style`, `assign_material_style`, `assign_representation_styles`, `edit_presentation_style`, `edit_surface_style`, `remove_style`, `remove_styled_representation`, `remove_surface_style`, `unassign_material_style`, `unassign_representation_styles`

```python
estilo = ifcopenshell.api.style.add_style(model, name='ConcreteGray')
ifcopenshell.api.style.add_surface_style(
    model,
    style=estilo,
    ifc_class='IfcSurfaceStyleRendering',
    attributes={
        'SurfaceColour': {'Name': None, 'Red': 0.6, 'Green': 0.6, 'Blue': 0.6},
        'ReflectanceMethod': 'FLAT',
        'Transparency': 0.0
    }
)
ifcopenshell.api.style.assign_material_style(model, material=mat, style=estilo, context=body)
```

---

## profile — Perfis de seção transversal

**Funções:** `add_parameterized_profile`, `add_arbitrary_profile`, `add_arbitrary_profile_with_voids`, `copy_profile`, `edit_profile`, `remove_profile`

```python
# Perfil paramétrico I
perfil_I = ifcopenshell.api.profile.add_parameterized_profile(model, ifc_class='IfcIShapeProfileDef')
ifcopenshell.api.profile.edit_profile(
    model, profile=perfil_I,
    attributes={
        'ProfileName': 'IPE300', 'ProfileType': 'AREA',
        'OverallWidth': 0.15, 'OverallDepth': 0.30,
        'WebThickness': 0.007, 'FlangeThickness': 0.0107
    }
)

# Perfil retangular
perfil_ret = ifcopenshell.api.profile.add_parameterized_profile(
    model, ifc_class='IfcRectangleProfileDef'
)
ifcopenshell.api.profile.edit_profile(
    model, profile=perfil_ret,
    attributes={'ProfileName': '300x300', 'XDim': 0.30, 'YDim': 0.30}
)

# Perfil circular
perfil_cir = ifcopenshell.api.profile.add_parameterized_profile(
    model, ifc_class='IfcCircleProfileDef'
)
ifcopenshell.api.profile.edit_profile(model, profile=perfil_cir, attributes={'Radius': 0.15})

# Perfil arbitrário (polígono)
perfil_arb = ifcopenshell.api.profile.add_arbitrary_profile(
    model,
    profile=[(0,0), (0.5,0), (0.5,0.5), (0,0.5)],
    name='Perfil Customizado'
)

# Classes de perfil: IfcIShapeProfileDef, IfcRectangleProfileDef, IfcCircleProfileDef,
#                    IfcLShapeProfileDef, IfcTShapeProfileDef, IfcCShapeProfileDef,
#                    IfcUShapeProfileDef, IfcZShapeProfileDef, IfcCircleHollowProfileDef,
#                    IfcRectangleHollowProfileDef, IfcEllipseProfileDef
```

---

## boundary — Space Boundaries

**Funções:** `assign_connection_geometry`, `copy_boundary`, `edit_attributes`, `remove_boundary`

```python
boundary = model.by_type('IfcRelSpaceBoundary')[0]
ifcopenshell.api.boundary.edit_attributes(
    model, entity=boundary,
    attributes={
        'PhysicalOrVirtualBoundary': 'PHYSICAL',
        'InternalOrExternalBoundary': 'EXTERNAL'
    }
)
ifcopenshell.api.boundary.copy_boundary(model, boundary=boundary)
ifcopenshell.api.boundary.remove_boundary(model, boundary=boundary)
```

---

## document — Documentos e referências

**Funções:** `add_information`, `edit_information`, `remove_information`, `add_reference`, `edit_reference`, `remove_reference`, `assign_document`, `unassign_document`

```python
doc = ifcopenshell.api.document.add_information(model)
ifcopenshell.api.document.edit_information(
    model, information=doc,
    attributes={
        'Identification': 'DWG-001',
        'Name': 'Planta Baixa Térreo',
        'Location': '/docs/DWG-001.pdf',
        'Description': 'Planta arquitetônica do térreo'
    }
)
ifcopenshell.api.document.assign_document(model, products=[elemento], document=doc)
ifcopenshell.api.document.unassign_document(model, products=[elemento], document=doc)
```

---

## constraint — Restrições e requisitos

**Funções:** `add_objective`, `edit_objective`, `add_metric`, `edit_metric`, `add_metric_reference`, `assign_constraint`, `unassign_constraint`, `remove_constraint`, `remove_metric`

```python
obj = ifcopenshell.api.constraint.add_objective(model)
ifcopenshell.api.constraint.edit_objective(
    model, objective=obj,
    attributes={'Name': 'Resistência ao Fogo', 'Intent': 'REI90'}
)
metric = ifcopenshell.api.constraint.add_metric(model, objective=obj)
ifcopenshell.api.constraint.assign_constraint(model, products=[parede], constraint=obj)
ifcopenshell.api.constraint.unassign_constraint(model, products=[parede], constraint=obj)
```

---

## project — Operações de projeto

**Funções:** `create_file`, `append_asset`, `assign_declaration`, `unassign_declaration`

```python
# Criar novo arquivo IFC
model = ifcopenshell.api.project.create_file(version='IFC4')

# Mesclar asset de uma biblioteca IFC externa
ifcopenshell.api.project.append_asset(
    model,
    library=model_biblioteca,  # outro ifcopenshell.file
    element=tipo_janela
)

# Declarar elemento em biblioteca
ifcopenshell.api.project.assign_declaration(
    model, definitions=[tipo_janela], relating_context=project
)
```

---

## sequence — Cronograma 4D

**Funções:** `add_work_plan`, `edit_work_plan`, `add_work_schedule`, `edit_work_schedule`, `copy_work_schedule`, `add_work_calendar`, `edit_work_calendar`, `add_work_time`, `edit_work_time`, `add_task`, `edit_task`, `duplicate_task`, `remove_task`, `add_task_time`, `edit_task_time`, `add_date_time`, `add_time_period`, `assign_process`, `assign_product`, `assign_sequence`, `edit_sequence`, `assign_lag_time`, `edit_lag_time`, `assign_recurrence_pattern`, `edit_recurrence_pattern`, `assign_work_plan`, `create_baseline`, `calculate_task_duration`, `cascade_schedule`, `recalculate_schedule`

```python
plano = ifcopenshell.api.sequence.add_work_plan(model, name='Plano de Obra')
cronograma = ifcopenshell.api.sequence.add_work_schedule(model, name='Físico', work_plan=plano)
tarefa = ifcopenshell.api.sequence.add_task(model, work_schedule=cronograma, name='Fundações')
ifcopenshell.api.sequence.edit_task(
    model, task=tarefa,
    attributes={'Status': 'NOTSTARTED', 'IsMilestone': False}
)
ifcopenshell.api.sequence.assign_product(model, relating_object=tarefa, products=[fundacao])
ifcopenshell.api.sequence.assign_sequence(
    model, relating_process=tarefa_ant, related_process=tarefa_pos
)
```

---

## cost — Orçamento 5D

**Funções:** `add_cost_schedule`, `edit_cost_schedule`, `copy_cost_schedule`, `remove_cost_schedule`, `add_cost_item`, `edit_cost_item`, `copy_cost_item`, `copy_cost_item_values`, `remove_cost_item`, `add_cost_item_quantity`, `edit_cost_item_quantity`, `remove_cost_item_quantity`, `assign_cost_item_quantity`, `unassign_cost_item_quantity`, `add_cost_value`, `edit_cost_value`, `edit_cost_value_formula`, `assign_cost_value`, `remove_cost_value`, `calculate_cost_item_resource_value`

```python
orcamento = ifcopenshell.api.cost.add_cost_schedule(model, name='Orçamento SINAPI 2024')
item = ifcopenshell.api.cost.add_cost_item(model, cost_schedule=orcamento)
ifcopenshell.api.cost.edit_cost_item(
    model, cost_item=item,
    attributes={'Name': 'Concreto fck=25MPa', 'Identification': '72013'}
)
valor = ifcopenshell.api.cost.add_cost_value(model, parent=item)
ifcopenshell.api.cost.edit_cost_value(
    model, cost_value=valor,
    attributes={'AppliedValue': 350.0}
)
```

---

## structural — Análise Estrutural

**Funções:** `add_structural_analysis_model`, `edit_structural_analysis_model`, `remove_structural_analysis_model`, `assign_structural_analysis_model`, `unassign_structural_analysis_model`, `add_structural_member_connection`, `add_structural_activity`, `add_structural_load_group`, `add_structural_load_case`, `edit_structural_load_case`, `remove_structural_load_case`, `add_structural_load`, `edit_structural_load`, `remove_structural_load`, `add_structural_boundary_condition`, `edit_structural_boundary_condition`, `remove_structural_boundary_condition`, `edit_structural_connection_cs`, `edit_structural_item_axis`, `assign_product`, `assign_to_building`, `remove_structural_connection_condition`

```python
modelo_est = ifcopenshell.api.structural.add_structural_analysis_model(
    model, name='Modelo Estrutural', predefined_type='LOADING_3D'
)
caso = ifcopenshell.api.structural.add_structural_load_case(model, analysis_model=modelo_est)
ifcopenshell.api.structural.edit_structural_load_case(
    model, load_case=caso,
    attributes={'Name': 'PP - Peso Próprio', 'ActionType': 'PERMANENT_G'}
)
carga = ifcopenshell.api.structural.add_structural_load(
    model, ifc_class='IfcStructuralLoadLinearForce'
)
ifcopenshell.api.structural.edit_structural_load(
    model, structural_load=carga,
    attributes={'LinearForceZ': -15000.0}
)
```

---

## alignment — Alinhamentos IFC4X3 (infraestrutura linear)

**Funções:** `create`, `create_as_polyline`, `create_as_offset_curve`, `create_by_pi_method`, `create_from_csv`, `add_vertical_layout`, `add_stationing_referent`, `add_zero_length_segment`, `create_layout_segment`, `create_representation`, `create_segment_representations`, `get_alignment`, `get_alignment_layouts`, `get_horizontal_layout`, `get_vertical_layout`, `get_cant_layout`, `get_child_alignments`, `get_parent_alignment`, `get_curve`, `get_basis_curve`, `get_alignment_start_station`, `distance_along_from_station`, `layout_horizontal_alignment_by_pi_method`, `layout_vertical_alignment_by_pi_method`, `name_segments`, `update_fallback_position`, `has_zero_length_segment`

```python
# Requer modelo IFC4X3
alinhamento = ifcopenshell.api.alignment.create(model, name='Eixo Principal')
ifcopenshell.api.alignment.create_as_polyline(
    model,
    alignment=alinhamento,
    points=[(0,0,0), (100,0,0), (200,50,0)]
)
# Consultar alinhamentos
aligns = ifcopenshell.api.alignment.get_alignment(model)
layouts = ifcopenshell.api.alignment.get_alignment_layouts(model, alignment=alinhamento)
```

---

## georeference — Georreferenciamento

```python
import ifcopenshell.api.georeference

ifcopenshell.api.georeference.add_georeferencing(model)
ifcopenshell.api.georeference.edit_georeferencing(
    model,
    coordinate_operation={
        'Eastings': 600000.0,
        'Northings': 7400000.0,
        'OrthogonalHeight': 20.0,
        'XAxisAbscissa': 1.0,
        'XAxisOrdinate': 0.0,
        'Scale': 1.0
    },
    projected_crs={
        'Name': 'SIRGAS 2000 / UTM zone 23S',
        'GeodeticDatum': 'SIRGAS 2000',
        'MapProjection': 'UTM',
        'MapZone': '23S',
        'MapUnit': unidade_metro
    }
)
```

---

## cogo — Coordinate Geometry (levantamento)

**Funções:** `add_survey_point`, `edit_survey_point`, `assign_survey_point`, `bearing2dd`

```python
ponto = ifcopenshell.api.cogo.add_survey_point(model, coordinates=(600100.0, 7400050.0, 22.5))
ifcopenshell.api.cogo.edit_survey_point(model, survey_point=ponto, attributes={'Name': 'VT-001'})
ifcopenshell.api.cogo.assign_survey_point(model, products=[elemento], survey_point=ponto)
dd = ifcopenshell.api.cogo.bearing2dd(bearing=(45, 30, 15))  # → 45.504167 graus decimais
```

---

## drawing — Anotações

**Funções:** `assign_product`, `edit_text_literal`, `unassign_product`

```python
# Associar produto a anotação de desenho técnico
ifcopenshell.api.drawing.assign_product(model, relating_product=elemento, related_object=anotacao)
ifcopenshell.api.drawing.edit_text_literal(
    model, text_literal=texto,
    attributes={'Literal': 'PAREDE P1', 'Path': 'RIGHT'}
)
```

---

## pset_template — Templates de Psets

```python
import ifcopenshell.api.pset_template

library = ifcopenshell.api.pset_template.create_template_file(author=pessoa)
template = ifcopenshell.api.pset_template.add_pset_template(
    library, name='Pset_OGSubFlexiblePipe'
)
prop = ifcopenshell.api.pset_template.add_prop_template(
    library, pset_template=template,
    name='NominalDiameter',
    description='Diâmetro nominal da linha flexível',
    primary_measure_type='IfcLengthMeasure'
)
```

---

## resource — Recursos

```python
recurso = ifcopenshell.api.resource.add_resource(
    model, ifc_class='IfcLaborResource', name='Pedreiro'
)
ifcopenshell.api.resource.edit_resource(
    model, resource=recurso, attributes={'Identification': 'MO-01'}
)
ifcopenshell.api.resource.assign_resource(
    model, relating_resource=recurso, related_object=tarefa
)
```

---

## Novidades v0.8.5 vs versões anteriores

| Módulo | Novidade |
|--------|----------|
| `alignment` | Módulo completo para IFC4X3 — infraestrutura linear |
| `cogo` | Novo — pontos de levantamento e conversão de bearing |
| `root` | `reassign_class` adicionado |
| `pset` | `unshare_pset` adicionado |
| `drawing` | Funções básicas de anotação |
| Geral | Estilo `module.function(model, ...)` preferido sobre `api.run(...)` |

---

## Fonte

Documentação oficial: https://docs.ifcopenshell.org/autoapi/ifcopenshell/api/index.html  
Versão: IfcOpenShell 0.8.5
