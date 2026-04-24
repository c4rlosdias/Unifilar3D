---
name: ifcopenshell-python
description: >
  Programação Python com IfcOpenShell para manipulação de modelos IFC (Industry Foundation Classes).
  Use esta skill sempre que o usuário pedir para ler, escrever, editar, consultar, validar ou analisar
  arquivos IFC usando Python. Também acione quando o assunto envolver: extração de quantitativos de
  modelos BIM, property sets, quantity sets, hierarquia espacial IFC, clash detection programático,
  criação de modelos IFC do zero, classificação automática de elementos, geração de relatórios a
  partir de modelos BIM, validação IDS, integração IfcOpenShell com Pandas/CSV/Excel, geometria
  IFC (bounding box, áreas, volumes), materiais e camadas IFC, ou qualquer automação BIM com Python.
  Mesmo que o usuário não mencione "IfcOpenShell" explicitamente, se a tarefa envolve manipulação
  programática de arquivos .ifc, esta skill é relevante. Inclui também orientação sobre o ecossistema
  (ifcopenshell.api, ifcopenshell.util, ifcopenshell.geom) e boas práticas OpenBIM.
---

# IfcOpenShell + Python — Guia de Programação BIM

Esta skill fornece orientação completa para programar com a biblioteca IfcOpenShell em Python, cobrindo desde operações básicas de leitura até manipulações avançadas de modelos IFC.

## Quando usar esta skill

- Leitura, escrita e edição de arquivos .ifc
- Consultas e filtros em modelos IFC (por tipo, GUID, propriedades)
- Extração de property sets, quantity sets e quantitativos
- Navegação na hierarquia espacial (Project > Site > Building > Storey)
- Criação de modelos IFC programaticamente
- Validação e verificação de qualidade de modelos
- Processamento geométrico (malhas, bounding boxes, áreas, volumes)
- Geração de relatórios e exportação para CSV/Excel/PDF
- Classificação automática de elementos (SINAPI, Uniclass, etc.)
- Clash detection programático simplificado

## Referências disponíveis

Para detalhes completos sobre cada tópico, consulte os arquivos de referência:

| Arquivo | Conteúdo | Quando ler |
|---------|----------|------------|
| `api-reference.md` | **Referência completa da `ifcopenshell.api` v0.8.5** — todos os 30+ módulos com assinaturas, parâmetros e exemplos (inclui `alignment`, `cogo`, `reassign_class`, `unshare_pset`) | Sempre que precisar criar, editar ou manipular modelos IFC via API |
| `core-api.md` | Leitura, consulta, atributos, hierarquia, psets, qtos, FQL, exportação CSV/Excel | Tarefas de leitura e consulta a modelos existentes |
| `create-edit.md` | Criação de modelos do zero, edição de elementos, materiais em camadas, posicionamento | Criar ou modificar modelos IFC |
| `advanced.md` | Validação, IDS, processamento geométrico, clash detection, classificação, relatórios PDF | Análise avançada, validação e automação |

**Regra de ouro:** leia `api-reference.md` para saber QUAL função usar e como chamá-la, depois leia o arquivo específico para padrões de código completos.

## Princípios fundamentais

### 1. Sempre prefira a API de alto nível

A `ifcopenshell.api` valida operações e mantém a integridade referencial do modelo. Na versão 0.8+ o estilo recomendado é chamar diretamente o módulo (sem `api.run`), mas ambos funcionam:

```python
import ifcopenshell
import ifcopenshell.api

# Estilo moderno (0.8+) — recomendado
ifcopenshell.api.attribute.edit_attributes(model, product=parede, attributes={'Name': 'Nova Parede'})

# Estilo legado — ainda funciona
ifcopenshell.api.run('attribute.edit_attributes', model, product=parede, attributes={'Name': 'Nova Parede'})

# Atribuição direta — funciona, mas sem validação de relacionamentos
parede.Name = 'Nova Parede'
```

### 2. Estrutura mínima de um arquivo IFC válido

Todo arquivo IFC precisa de: IfcProject + Unidades + Contexto Geométrico + Hierarquia Espacial. Sem isso, o arquivo será rejeitado por viewers e ferramentas BIM.

```python
import ifcopenshell
import ifcopenshell.api

model = ifcopenshell.file(schema='IFC4')
project = ifcopenshell.api.root.create_entity(model, ifc_class='IfcProject', name='Projeto')
ifcopenshell.api.unit.assign_unit(model)
ctx = ifcopenshell.api.context.add_context(model, context_type='Model')
body = ifcopenshell.api.context.add_context(
    model, context_type='Model', context_identifier='Body',
    target_view='MODEL_VIEW', parent=ctx)
```

### 3. Padrão de consulta com utilitários

Os módulos `ifcopenshell.util.*` são essenciais — economizam dezenas de linhas de código:

```python
import ifcopenshell.util.element as util_el

# Hierarquia
container = util_el.get_container(elemento)     # pavimento
tipo = util_el.get_type(elemento)               # IfcWallType, etc.
material = util_el.get_material(elemento)       # material vinculado
decomp = util_el.get_decomposition(pavimento)   # elementos contidos

# Propriedades
psets = util_el.get_psets(elemento)                       # todos os psets + qtos
psets = util_el.get_psets(elemento, psets_only=True)      # só property sets
qtos = util_el.get_psets(elemento, qtos_only=True)        # só quantitativos
valor = util_el.get_pset(elemento, 'Pset_WallCommon', 'FireRating')
```

### 4. Processamento geométrico — sempre com try/except

Nem todos os elementos possuem geometria válida. Sempre proteja chamadas geométricas:

```python
import ifcopenshell.geom
import numpy as np

settings = ifcopenshell.geom.settings()
settings.set(settings.USE_WORLD_COORDS, True)

for elem in model.by_type('IfcWall'):
    try:
        shape = ifcopenshell.geom.create_shape(settings, elem)
        verts = np.array(shape.geometry.verts).reshape(-1, 3)
        bbox_min, bbox_max = verts.min(axis=0), verts.max(axis=0)
    except Exception:
        continue  # elemento sem geometria válida
```

### 5. FQL — Filtro Query Language

Para consultas complexas, o seletor FQL é mais legível que list comprehensions aninhadas:

```python
import ifcopenshell.util.selector as selector

# Paredes externas com resistência ao fogo
resultado = selector.filter_elements(model,
    'IfcWall, Pset_WallCommon.IsExternal = True, Pset_WallCommon.FireRating != None')
```

## Erros comuns e soluções rápidas

| Erro | Causa provável | Solução |
|------|---------------|---------|
| `RuntimeError: schema not found` | Instalação corrompida | `pip install --force-reinstall ifcopenshell` |
| Geometria retorna vazio | Elemento sem representação | Verificar `elem.Representation` antes de processar |
| `get_psets()` retorna `{}` | Nenhum Pset vinculado ao elemento | Verificar se há `IfcRelDefinesByProperties` no modelo |
| KeyError em atributo | Atributo não existe neste schema/classe | Consultar `elem.get_info()` para ver atributos válidos |
| Modelo inválido ao salvar | Falta hierarquia espacial ou unidades | Garantir IfcProject > Site > Building > Storey + unidades |
| Encoding error em CSV | Caracteres especiais (acentos) | Usar `encoding='utf-8-sig'` no `open()` |
| `get_container()` retorna None | Elemento não vinculado a pavimento | Usar `ifcopenshell.api.spatial.assign_container(...)` |

## Instalação

```bash
pip install ifcopenshell          # básico
pip install ifcopenshell[all]     # completo com todas as dependências
```

Verificação: `python -c "import ifcopenshell; print(ifcopenshell.version)"`
