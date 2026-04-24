# Referência: Criação e Edição de Modelos IFC

Este documento cobre a criação de modelos IFC do zero, edição de elementos existentes, materiais e posicionamento geométrico.

## Índice

1. Criando um arquivo IFC do zero
2. Adicionando elementos
3. Adicionando propriedades
4. Materiais e camadas
5. Editando atributos
6. Editando propriedades existentes
7. Movendo e rotacionando elementos
8. Removendo elementos
9. Renomeação em lote
10. Salvando o modelo

---

## 1. Criando um arquivo IFC do zero

Todo arquivo IFC válido precisa de: IfcProject + Unidades + Contexto Geométrico + Hierarquia Espacial.

```python
import ifcopenshell
import ifcopenshell.api as api

# Criar arquivo com schema IFC4
model = ifcopenshell.file(schema='IFC4')

# 1. Projeto
project = api.run('root.create_entity', model,
    ifc_class='IfcProject', name='Meu Projeto')

# 2. Unidades (SI - metro)
api.run('unit.assign_unit', model)

# 3. Contexto geométrico
ctx = api.run('context.add_context', model, context_type='Model')
body = api.run('context.add_context', model,
    context_type='Model',
    context_identifier='Body',
    target_view='MODEL_VIEW',
    parent=ctx)

# 4. Hierarquia espacial
site = api.run('root.create_entity', model,
    ifc_class='IfcSite', name='Terreno')
api.run('aggregate.assign_object', model,
    relating_object=project, products=[site])

building = api.run('root.create_entity', model,
    ifc_class='IfcBuilding', name='Edifício Principal')
api.run('aggregate.assign_object', model,
    relating_object=site, products=[building])

storey = api.run('root.create_entity', model,
    ifc_class='IfcBuildingStorey', name='Térreo')
api.run('aggregate.assign_object', model,
    relating_object=building, products=[storey])
```

## 2. Adicionando elementos

```python
# Criar uma parede
parede = api.run('root.create_entity', model,
    ifc_class='IfcWall', name='Parede Externa 01')

# Vincular ao pavimento
api.run('spatial.assign_container', model,
    relating_structure=storey, products=[parede])

# Adicionar geometria (representação extrudada)
repr_item = api.run('geometry.add_wall_representation', model,
    context=body, length=5.0, height=2.8, thickness=0.2)

api.run('geometry.assign_representation', model,
    product=parede, representation=repr_item)

# Posicionar a parede
import ifcopenshell.util.placement as util_place
api.run('geometry.edit_object_placement', model,
    product=parede,
    matrix=util_place.a2p(
        [0.0, 0.0, 0.0],   # origem (x, y, z)
        [0.0, 0.0, 1.0],   # direção Z
        [1.0, 0.0, 0.0]))  # direção X
```

## 3. Adicionando propriedades

```python
# Criar property set padrão IFC
pset = api.run('pset.add_pset', model,
    product=parede, name='Pset_WallCommon')

api.run('pset.edit_pset', model, pset=pset,
    properties={
        'IsExternal': True,
        'FireRating': 'EI 120',
        'ThermalTransmittance': 0.35,
        'Reference': 'PAR-EXT-01',
        'LoadBearing': True,
    })

# Property set customizado (ex: referência SINAPI)
pset_custom = api.run('pset.add_pset', model,
    product=parede, name='SINAPI_Referencia')

api.run('pset.edit_pset', model, pset=pset_custom,
    properties={
        'CodigoSINAPI': '87515',
        'Descricao': 'Alvenaria bloco cerâmico 14x19x29',
        'UnidadeMedida': 'm²',
        'CustoUnitario': 62.47,
    })
```

## 4. Materiais e camadas

### Material simples

```python
material = api.run('material.add_material', model, name='Concreto C30')
api.run('material.assign_material', model,
    products=[parede], material=material)
```

### Material em camadas (paredes compostas)

```python
mat_layer_set = api.run('material.add_material_set', model,
    name='Parede Composta', set_type='IfcMaterialLayerSet')

reboco_int = api.run('material.add_material', model, name='Reboco Interno')
alvenaria = api.run('material.add_material', model, name='Alvenaria Bloco Cerâmico')
reboco_ext = api.run('material.add_material', model, name='Reboco Externo')

api.run('material.add_layer', model,
    layer_set=mat_layer_set, material=reboco_int, thickness=0.02)
api.run('material.add_layer', model,
    layer_set=mat_layer_set, material=alvenaria, thickness=0.14)
api.run('material.add_layer', model,
    layer_set=mat_layer_set, material=reboco_ext, thickness=0.02)

api.run('material.assign_material', model,
    products=[parede], material=mat_layer_set)
```

## 5. Editando atributos

```python
model = ifcopenshell.open('modelo.ifc')
parede = model.by_type('IfcWall')[0]

# Via API (recomendado — valida automaticamente)
api.run('attribute.edit_attributes', model,
    product=parede,
    attributes={'Name': 'Parede Editada', 'Description': 'Modificada via API'})

# Direto (funciona, mas sem validação)
parede.Name = 'Parede Editada'
```

## 6. Editando propriedades existentes

```python
import ifcopenshell.util.element as util_el

psets = util_el.get_psets(parede)
pset_id = psets['Pset_WallCommon']['id']
pset = model.by_id(pset_id)

# Atualizar propriedades
api.run('pset.edit_pset', model, pset=pset,
    properties={
        'FireRating': 'EI 180',        # atualizar existente
        'AcousticRating': 'Rw 45',     # adicionar nova
    })

# Remover uma propriedade (setar como None)
api.run('pset.edit_pset', model, pset=pset,
    properties={'LoadBearing': None})
```

## 7. Movendo e rotacionando elementos

```python
import math
import ifcopenshell.util.placement as util_place

# Mover para nova posição
nova_pos = util_place.a2p(
    [3.0, 2.0, 0.0],    # nova origem
    [0.0, 0.0, 1.0],    # direção Z
    [1.0, 0.0, 0.0])    # direção X

api.run('geometry.edit_object_placement', model,
    product=parede, matrix=nova_pos)

# Rotacionar 90 graus no eixo Z
angulo = math.radians(90)
rotacionado = util_place.a2p(
    [0.0, 0.0, 0.0],
    [0.0, 0.0, 1.0],
    [math.cos(angulo), math.sin(angulo), 0.0])

api.run('geometry.edit_object_placement', model,
    product=parede, matrix=rotacionado)
```

## 8. Removendo elementos

```python
# Remove o elemento e seus relacionamentos associados
parede_remover = model.by_type('IfcWall')[-1]
api.run('root.remove_product', model, product=parede_remover)
```

## 9. Renomeação em lote

```python
import ifcopenshell.util.element as util_el

# Por pavimento + índice
for i, parede in enumerate(model.by_type('IfcWall'), 1):
    container = util_el.get_container(parede)
    pav = container.Name if container else 'Sem_Pav'
    parede.Name = f'PAR-{pav}-{i:03d}'

# Por tipo + classificação
for parede in model.by_type('IfcWall'):
    tipo = util_el.get_type(parede)
    if tipo:
        pset = util_el.get_pset(parede, 'Pset_WallCommon')
        ext = 'EXT' if pset and pset.get('IsExternal') else 'INT'
        parede.Name = f'{ext}-{tipo.Name}'
```

## 10. Salvando o modelo

```python
model.write('modelo_editado.ifc')
print(f'Salvo com {len(list(model))} entidades')
```
