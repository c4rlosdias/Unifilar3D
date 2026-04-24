# Referência: Funcionalidades Avançadas

Este documento cobre validação, processamento geométrico, relatórios, clash detection e classificação automática.

## Índice

1. Validação de modelos
2. Verificações customizadas de qualidade
3. IDS (Information Delivery Specification)
4. Processamento geométrico
5. Cálculo de áreas e volumes
6. Extração de quantitativos para relatórios
7. Resumo por pavimento e tipo
8. Clash detection simplificado
9. Classificação automática de elementos
10. Geração de relatórios em PDF

---

## 1. Validação de modelos

```python
import ifcopenshell.validate

model = ifcopenshell.open('modelo.ifc')
logger = ifcopenshell.validate.json_logger()
ifcopenshell.validate.validate(model, logger)

if logger.statements:
    print(f'Encontrados {len(logger.statements)} problemas:')
    for stmt in logger.statements:
        print(f'  [{stmt["severity"]}] {stmt["message"]}')
else:
    print('Modelo válido!')
```

## 2. Verificações customizadas de qualidade

```python
import ifcopenshell.util.element as util_el

def verificar_modelo(model):
    problemas = []

    # 1. Elementos sem nome
    for elem in model.by_type('IfcElement'):
        if not elem.Name or elem.Name.strip() == '':
            problemas.append(f'{elem.is_a()} #{elem.id()} sem nome')

    # 2. Paredes sem Pset_WallCommon
    for parede in model.by_type('IfcWall'):
        pset = util_el.get_pset(parede, 'Pset_WallCommon')
        if not pset:
            problemas.append(f'Parede "{parede.Name}" sem Pset_WallCommon')

    # 3. Elementos sem container espacial
    for elem in model.by_type('IfcElement'):
        container = util_el.get_container(elem)
        if not container:
            problemas.append(f'{elem.is_a()} "{elem.Name}" sem pavimento')

    # 4. Apenas 1 IfcProject
    projetos = model.by_type('IfcProject')
    if len(projetos) != 1:
        problemas.append('Modelo deve ter exatamente 1 IfcProject')

    # 5. Elementos sem tipo
    for elem in model.by_type('IfcElement'):
        tipo = util_el.get_type(elem)
        if not tipo:
            problemas.append(f'{elem.is_a()} "{elem.Name}" sem tipo definido')

    return problemas

problemas = verificar_modelo(model)
for p in problemas:
    print(f'  [AVISO] {p}')
print(f'\nTotal: {len(problemas)} problemas encontrados')
```

## 3. IDS (Information Delivery Specification)

O IDS é o padrão buildingSMART para especificar requisitos de informação que um modelo IFC deve atender.

```python
import ifcopenshell.ids as ids

my_ids = ids.open('requisitos.ids')
my_ids.validate(model)

for spec in my_ids.specifications:
    print(f'Especificação: {spec.name}')
    print(f'  Status: {spec.status}')
    if not spec.status:
        for req in spec.requirements:
            if not req.status:
                print(f'  Falha: {req}')
```

## 4. Processamento geométrico

O processamento geométrico triangula as representações IFC em malhas 3D.

```python
import ifcopenshell.geom
import numpy as np

settings = ifcopenshell.geom.settings()
settings.set(settings.USE_WORLD_COORDS, True)

parede = model.by_type('IfcWall')[0]
shape = ifcopenshell.geom.create_shape(settings, parede)

# Vértices e faces
vertices = shape.geometry.verts    # lista flat [x1,y1,z1,x2,y2,z2,...]
faces = shape.geometry.faces       # índices dos triângulos

# Reorganizar em array numpy
verts = np.array(vertices).reshape(-1, 3)
print(f'Total de vértices: {len(verts)}')
print(f'Bounding box min: {verts.min(axis=0)}')
print(f'Bounding box max: {verts.max(axis=0)}')
```

### Obter placement (posição e orientação)

```python
import ifcopenshell.util.placement

matrix = ifcopenshell.util.placement.get_local_placement(parede.ObjectPlacement)
print(f'Posição: {matrix[:3, 3]}')  # vetor de translação
```

**Importante:** sempre use try/except ao processar geometria, pois nem todos os elementos têm representação válida.

## 5. Cálculo de áreas e volumes

```python
def calcular_area_volume(model, elemento):
    """Calcula área de superfície e volume via triangulação."""
    settings = ifcopenshell.geom.settings()
    settings.set(settings.USE_WORLD_COORDS, True)
    shape = ifcopenshell.geom.create_shape(settings, elemento)

    verts = np.array(shape.geometry.verts).reshape(-1, 3)
    faces = np.array(shape.geometry.faces).reshape(-1, 3)

    area = 0.0
    volume = 0.0
    for f in faces:
        v0, v1, v2 = verts[f[0]], verts[f[1]], verts[f[2]]
        cross = np.cross(v1 - v0, v2 - v0)
        area += np.linalg.norm(cross) / 2.0
        volume += np.dot(v0, cross) / 6.0

    return abs(area), abs(volume)

for parede in model.by_type('IfcWall')[:5]:
    try:
        a, v = calcular_area_volume(model, parede)
        print(f'{parede.Name}: Área={a:.2f}m², Vol={v:.3f}m³')
    except Exception:
        print(f'{parede.Name}: sem geometria válida')
```

**Dica de performance:** para modelos grandes, use multiprocessing ou processe apenas os elementos necessários. O IfcOpenShell também suporta iterator para processar geometria em lote.

## 6. Extração de quantitativos para relatórios

```python
import csv
from collections import defaultdict

def extrair_quantitativos(model):
    dados = []
    for elem in model.by_type('IfcElement'):
        container = util_el.get_container(elem)
        tipo = util_el.get_type(elem)
        material = util_el.get_material(elem)
        qtos = util_el.get_psets(elem, qtos_only=True)
        qto_values = {}
        for qto_name, props in qtos.items():
            for k, v in props.items():
                if k != 'id' and v is not None:
                    qto_values[k] = v

        dados.append({
            'Classe': elem.is_a(),
            'Nome': elem.Name or '',
            'Tipo': tipo.Name if tipo else '',
            'Pavimento': container.Name if container else '',
            'Material': material.Name if material and hasattr(material, 'Name') else '',
            'Area': qto_values.get('NetSideArea', qto_values.get('NetArea', '')),
            'Volume': qto_values.get('NetVolume', qto_values.get('GrossVolume', '')),
            'Comprimento': qto_values.get('Length', ''),
        })
    return dados

dados = extrair_quantitativos(model)
with open('quantitativos.csv', 'w', newline='', encoding='utf-8-sig') as f:
    writer = csv.DictWriter(f, fieldnames=dados[0].keys())
    writer.writeheader()
    writer.writerows(dados)
```

## 7. Resumo por pavimento e tipo

```python
from collections import defaultdict

def resumo_por_pavimento(model):
    resumo = defaultdict(lambda: defaultdict(int))
    for elem in model.by_type('IfcElement'):
        container = util_el.get_container(elem)
        pav = container.Name if container else 'Sem Pavimento'
        resumo[pav][elem.is_a()] += 1

    for pav, tipos in sorted(resumo.items()):
        print(f'\n=== {pav} ===')
        total = 0
        for tipo, qtd in sorted(tipos.items()):
            print(f'  {tipo}: {qtd}')
            total += qtd
        print(f'  TOTAL: {total}')

resumo_por_pavimento(model)
```

## 8. Clash detection simplificado

Clash detection baseado em bounding boxes (AABB). Para detecção precisa, considere usar bibliotecas de geometria computacional.

```python
import ifcopenshell.geom
import numpy as np

def bounding_boxes(model, ifc_class):
    settings = ifcopenshell.geom.settings()
    settings.set(settings.USE_WORLD_COORDS, True)
    bboxes = []
    for elem in model.by_type(ifc_class):
        try:
            shape = ifcopenshell.geom.create_shape(settings, elem)
            verts = np.array(shape.geometry.verts).reshape(-1, 3)
            bboxes.append({
                'elem': elem,
                'min': verts.min(axis=0),
                'max': verts.max(axis=0),
            })
        except Exception:
            continue
    return bboxes

def verificar_colisoes(bboxes_a, bboxes_b, tolerancia=0.01):
    colisoes = []
    for a in bboxes_a:
        for b in bboxes_b:
            if (np.all(a['min'] - tolerancia <= b['max']) and
                np.all(a['max'] + tolerancia >= b['min'])):
                colisoes.append((a['elem'], b['elem']))
    return colisoes

# Exemplo: tubulações vs estrutura
bb_pipes = bounding_boxes(model, 'IfcPipeSegment')
bb_beams = bounding_boxes(model, 'IfcBeam')
clashes = verificar_colisoes(bb_pipes, bb_beams)

for pipe, beam in clashes:
    print(f'CLASH: {pipe.Name} x {beam.Name}')
```

## 9. Classificação automática de elementos

```python
import ifcopenshell.api as api
import ifcopenshell.util.element as util_el

def classificar_elementos(model):
    mapa_sinapi = {
        ('IfcWall', True): {'codigo': '87515', 'desc': 'Alvenaria bloco cerâmico vedação'},
        ('IfcWall', False): {'codigo': '87516', 'desc': 'Alvenaria bloco cerâmico interna'},
        ('IfcSlab', None): {'codigo': '92916', 'desc': 'Laje maciça concreto armado'},
        ('IfcColumn', None): {'codigo': '92717', 'desc': 'Pilar concreto armado'},
    }

    for elem in model.by_type('IfcElement'):
        pset = util_el.get_pset(elem, 'Pset_WallCommon') or {}
        is_ext = pset.get('IsExternal')
        classe = elem.is_a()

        chave = (classe, is_ext)
        if chave not in mapa_sinapi:
            chave = (classe, None)

        if chave in mapa_sinapi:
            ref = mapa_sinapi[chave]
            pset_sinapi = api.run('pset.add_pset', model,
                product=elem, name='SINAPI')
            api.run('pset.edit_pset', model, pset=pset_sinapi,
                properties={
                    'Codigo': ref['codigo'],
                    'Descricao': ref['desc'],
                })

classificar_elementos(model)
model.write('modelo_classificado.ifc')
```

## 10. Geração de relatórios em PDF

```python
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table as RLTable, TableStyle
from reportlab.platypus import Paragraph as RLPara
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from collections import defaultdict

def gerar_relatorio_pdf(model, caminho='relatorio_ifc.pdf'):
    doc = SimpleDocTemplate(caminho, pagesize=A4)
    styles = getSampleStyleSheet()
    elementos_doc = []

    projeto = model.by_type('IfcProject')[0]
    elementos_doc.append(RLPara(f'Relatório BIM: {projeto.Name}', styles['Title']))

    headers = ['Tipo', 'Qtd', 'Área Total (m²)']
    dados_tabela = [headers]

    tipos_contagem = defaultdict(lambda: {'qtd': 0, 'area': 0})
    for elem in model.by_type('IfcElement'):
        classe = elem.is_a()
        qtos = util_el.get_psets(elem, qtos_only=True)
        area = 0
        for qto in qtos.values():
            area = qto.get('NetSideArea', qto.get('NetArea', 0)) or 0
        tipos_contagem[classe]['qtd'] += 1
        tipos_contagem[classe]['area'] += float(area) if area else 0

    for tipo, vals in sorted(tipos_contagem.items()):
        dados_tabela.append([tipo, str(vals['qtd']), f"{vals['area']:.2f}"])

    tabela = RLTable(dados_tabela)
    tabela.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1B4F72')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
    ]))
    elementos_doc.append(tabela)
    doc.build(elementos_doc)

gerar_relatorio_pdf(model)
```
