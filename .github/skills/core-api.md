# Referência: Leitura, Consulta e Navegação em Modelos IFC

Este documento cobre todas as operações de leitura e consulta de modelos IFC com IfcOpenShell.

## Índice

1. Abrindo arquivos
2. Buscando entidades
3. Atributos de entidades
4. Hierarquia espacial
5. Property Sets
6. Quantity Sets
7. Relacionamentos
8. Seletores e filtros avançados (FQL)
9. Exportação para DataFrame/CSV

---

## 1. Abrindo arquivos

```python
import ifcopenshell

model = ifcopenshell.open('modelo.ifc')
print(f'Schema: {model.schema}')           # 'IFC4', 'IFC2X3', etc.
print(f'Total de entidades: {len(list(model))}')
```

## 2. Buscando entidades

### Por tipo (mais comum)

```python
paredes = model.by_type('IfcWall')
portas = model.by_type('IfcDoor')
janelas = model.by_type('IfcWindow')
lajes = model.by_type('IfcSlab')
colunas = model.by_type('IfcColumn')
vigas = model.by_type('IfcBeam')
tubos = model.by_type('IfcPipeSegment')
espacos = model.by_type('IfcSpace')
pavimentos = model.by_type('IfcBuildingStorey')

for parede in model.by_type('IfcWall'):
    print(f'{parede.Name} (ID: {parede.GlobalId})')
```

### Por GlobalId

```python
entidade = model.by_guid('2O2Fr$t4X7Zf8NOew3FLOH')
```

### Por Step ID numérico

```python
entidade = model.by_id(123)
```

## 3. Atributos de entidades

```python
parede = model.by_type('IfcWall')[0]

parede.GlobalId          # '2O2Fr$t4X7Zf8NOew3FLOH'
parede.Name              # 'Parede Externa 01'
parede.Description       # 'Parede de alvenaria'
parede.ObjectType        # 'STANDARD'
parede.is_a()            # 'IfcWall'
parede.is_a('IfcElement')  # True (herança)
parede.id()              # 123 (Step ID)

# Todos os atributos como dicionário
info = parede.get_info()
for attr, valor in info.items():
    print(f'{attr}: {valor}')
```

## 4. Hierarquia espacial

Hierarquia padrão: IfcProject > IfcSite > IfcBuilding > IfcBuildingStorey > Elementos.

```python
import ifcopenshell.util.element as util_el

# Em qual pavimento está o elemento?
container = util_el.get_container(parede)
print(f'Pavimento: {container.Name}')

# Todos os elementos de um pavimento
pavimento = model.by_type('IfcBuildingStorey')[0]
elementos = util_el.get_decomposition(pavimento)
for elem in elementos:
    print(f'{elem.is_a()}: {elem.Name}')
```

## 5. Property Sets

Property sets (Psets) são conjuntos de propriedades vinculados a elementos. Existem Psets padronizados pelo IFC (ex: Pset_WallCommon) e Psets customizados.

```python
import ifcopenshell.util.element as util_el

parede = model.by_type('IfcWall')[0]

# Obter TODOS os property sets (psets + qtos)
psets = util_el.get_psets(parede)

# Apenas property sets (sem quantitativos)
psets = util_el.get_psets(parede, psets_only=True)

# Iterar
for nome_pset, propriedades in psets.items():
    print(f'\nPset: {nome_pset}')
    for prop, valor in propriedades.items():
        if prop != 'id':
            print(f'  {prop}: {valor}')

# Pset específico
pset_wall = util_el.get_pset(parede, 'Pset_WallCommon')
if pset_wall:
    print(pset_wall.get('FireRating'))
    print(pset_wall.get('IsExternal'))

# Propriedade específica diretamente
fire = util_el.get_pset(parede, 'Pset_WallCommon', 'FireRating')
```

## 6. Quantity Sets

Quantity sets (Qtos) contêm quantitativos geométricos como área, volume, comprimento.

```python
qtos = util_el.get_psets(parede, qtos_only=True)
for nome_qto, quantidades in qtos.items():
    print(f'\nQto: {nome_qto}')
    for q, v in quantidades.items():
        if q != 'id':
            print(f'  {q}: {v}')
```

**Quantitativos comuns por classe:**

- IfcWall (Qto_WallBaseQuantities): Length, Width, Height, GrossSideArea, NetSideArea, GrossVolume, NetVolume
- IfcSlab (Qto_SlabBaseQuantities): Width, Perimeter, GrossArea, NetArea, GrossVolume, NetVolume
- IfcColumn (Qto_ColumnBaseQuantities): Length, CrossSectionArea, GrossSurfaceArea, GrossVolume, NetVolume
- IfcBeam (Qto_BeamBaseQuantities): Length, CrossSectionArea, GrossSurfaceArea, GrossVolume, NetVolume
- IfcDoor (Qto_DoorBaseQuantities): Width, Height, Area
- IfcWindow (Qto_WindowBaseQuantities): Width, Height, Area
- IfcSpace (Qto_SpaceBaseQuantities): GrossFloorArea, NetFloorArea, GrossVolume, NetVolume, Height

## 7. Relacionamentos

```python
parede = model.by_type('IfcWall')[0]

# Tipo do elemento
tipo = util_el.get_type(parede)
if tipo:
    print(f'Tipo: {tipo.Name}')

# Material
material = util_el.get_material(parede)
if material:
    print(f'Material: {material.is_a()} - {material.Name}')

# Relações inversas
for rel in model.get_inverse(parede):
    print(f'{rel.is_a()}')

# Aberturas em paredes (portas, janelas)
for rel in parede.HasOpenings:
    abertura = rel.RelatedOpeningElement
    for fill_rel in abertura.HasFillings:
        elem = fill_rel.RelatedBuildingElement
        print(f'{elem.is_a()} - {elem.Name}')
```

## 8. Seletores e filtros avançados

### List comprehensions (simples)

```python
# Paredes externas
paredes_ext = [
    w for w in model.by_type('IfcWall')
    if util_el.get_pset(w, 'Pset_WallCommon', 'IsExternal')
]

# Portas largas (> 0.9m)
portas_largas = [
    d for d in model.by_type('IfcDoor')
    if d.OverallWidth and d.OverallWidth > 0.9
]

# Elementos de um pavimento específico
terreo = next(
    s for s in model.by_type('IfcBuildingStorey')
    if s.Name and 'Térreo' in s.Name
)
elems_terreo = util_el.get_decomposition(terreo)
```

### FQL — Filter Query Language (complexo)

```python
import ifcopenshell.util.selector as selector

paredes = selector.filter_elements(model, 'IfcWall')
ext = selector.filter_elements(model, 'IfcWall, Name *= "Externa"')
fire_rated = selector.filter_elements(model,
    'IfcWall, Pset_WallCommon.FireRating = "EI 120"')
resultado = selector.filter_elements(model,
    'IfcWall, Pset_WallCommon.IsExternal = True, Pset_WallCommon.FireRating != None')
```

**Operadores FQL:** `=` (igual), `!=` (diferente), `*=` (contém), `>`, `<`, `>=`, `<=` (comparação numérica)

## 9. Exportação

### Para CSV

```python
import csv

dados = []
for elem in model.by_type('IfcElement'):
    container = util_el.get_container(elem)
    tipo = util_el.get_type(elem)
    qtos = util_el.get_psets(elem, qtos_only=True)
    qto_vals = {}
    for qto_name, props in qtos.items():
        for k, v in props.items():
            if k != 'id' and v is not None:
                qto_vals[k] = v
    dados.append({
        'Classe': elem.is_a(),
        'Nome': elem.Name or '',
        'Tipo': tipo.Name if tipo else '',
        'Pavimento': container.Name if container else '',
        'Area': qto_vals.get('NetSideArea', qto_vals.get('NetArea', '')),
        'Volume': qto_vals.get('NetVolume', qto_vals.get('GrossVolume', '')),
    })

with open('quantitativos.csv', 'w', newline='', encoding='utf-8-sig') as f:
    writer = csv.DictWriter(f, fieldnames=dados[0].keys())
    writer.writeheader()
    writer.writerows(dados)
```

### Para Pandas DataFrame

```python
import pandas as pd

def ifc_para_dataframe(model, ifc_class='IfcElement'):
    registros = []
    for elem in model.by_type(ifc_class):
        reg = {'GlobalId': elem.GlobalId, 'Classe': elem.is_a(), 'Nome': elem.Name}
        psets = util_el.get_psets(elem)
        for pset_name, props in psets.items():
            for k, v in props.items():
                if k != 'id':
                    reg[f'{pset_name}.{k}'] = v
        registros.append(reg)
    return pd.DataFrame(registros)

df = ifc_para_dataframe(model, 'IfcWall')
df.to_excel('paredes.xlsx', index=False)
```
