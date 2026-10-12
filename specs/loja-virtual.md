# Loja virtual (Bling Loja Virtual / Tray) — tema e produtos

> Achados validados (não redescobrir). O que **não** foi verificado está em
> [Não verificado](#não-verificado). Valores locais vêm do `.env` (ver `.env.example`):
> `THEME_PREFIX` (prefixo de arquivos/classes próprios) e `THEME_MARK` (marcador dos
> comentários em arquivos originais). Placeholders: `<LOJA_ID>`, `<subdominio>`, `<themeId>`.

## Escopo

A Bling Loja Virtual é a plataforma **Tray**. Fica **fora da API v3** do Bling (as outras
specs): tema, catálogo e vitrine são administrados pelo painel da loja e pelo **Studio**
da Tray. O ERP só alimenta o catálogo (ver [Produtos](#produtos-no-erp--na-loja)).

## Acesso

- Painel/vitrine: `https://<subdominio>.commercesuite.com.br` (admin em `/admin/`, temas em
  `/studio-app/themes`). Login **sempre feito pelo usuário** (agente não digita senha).
- API do Studio: `https://app.studio.tray.net.br/api/v1/theme-installs/<themeId>/assets`.
  Token = `localStorage.token` de uma página da loja já logada (ex.: `/studio-app/themes`).
  **Nunca imprimir o token.** Usar de dentro do navegador (`fetch`), não por script local.
- O painel da loja é **iframe**: ferramentas de navegador não clicam nele (o usuário faz).
  A tela de produtos do ERP (`bling.com.br/produtos.php`) não é iframe e pode ser operada.

## Temas

- **Só um tema publicado por vez** e **não existe "despublicar"**: publica-se outro.
- **HTML/assets só editam em tema não publicado.** No publicado a API responde
  "Tema está publicado".
- Tema não publicado se vê em
  `https://<subdominio>.commercesuite.com.br/<qualquer-url>?loja=<LOJA_ID>&opencode_theme=<uuid>`
  (uuid = o do tema, obtido na pré-visualização do Studio). Define o cookie `opencode_preview`,
  que **gruda**: pode mostrar tema errado depois. Resetar em
  `/mvc/store/home/reset_opencode_preview?loja=<LOJA_ID>`.
- Páginas públicas ficam em cache (`max-age=14400`, ~4 h). O preview reflete edição na hora;
  use `cache: 'reload'` / `?_=<timestamp>` ao conferir por script.
- Instalar tema novo cria outra instalação (`themeId` novo); fácil criar duplicatas sem querer.

## Arquitetura do tema Padrão 3.0

```
layouts/   default.html, ajax.html, error.html   # esqueleto; default inclui os elements
pages/     home, catalog, product, search        # só montam seções
elements/  header, footer, styles, scripts, css-variables, head-metas, ...
  snippets/  product_form, product-tags, product-unavailable, brands, video, ...
css/       main, sidecart, page-*, <seção>.css, swiper, photoswipe, fonts/
js/        main, sidecart, page-*, <seção>.js, vendor/
configs/   settings.json + editor/sections/*.json  # opções do editor visual
```

- `layouts/default.html` inclui, em ordem: `head-metas`, `css-variables`, `styles`, modais,
  `sidecart`, `menu-mobile`, `header`, `footer`, ..., `scripts`. Todo CSS/JS global passa
  por `elements/styles.html` e `elements/scripts.html`.
- **Três jeitos de ligar CSS/JS** (JS e CSS não se ligam entre si; só compartilham o nome):
  1. **Global**: `<link href="{{ asset('css/x.css') }}">` direto em `styles.html`
     (`swiper`, `main`, `sidecart`) ou `<script src="{{ asset('js/x.js') }}">` em `scripts.html`.
  2. **Por página**: dentro do mesmo arquivo, com `{% if 'product' in pages.current %}`.
     Valores vistos: `product`, `catalog`, `search`, `contact`, `depoimentos`,
     `busca_noticias`, `noticia`, `newsletter`, `register`, `comparador`.
  3. **Por seção**: o snippet chama o próprio par (ex.: `snippets/brands.html` liga
     `css/brands.css` e `js/brands.js`). `pages/home.html` só monta as seções ativas no editor.
- **Cores e fonte** viram variáveis CSS (`--color_border`, `--color_base`, `--color_font`,
  `--font_family`, ...) em `elements/css-variables.html`, a partir do editor visual. Use essas
  variáveis em vez de cores fixas.
- O campo "Estilo Customizado" do editor é emitido como `<style>` no fim de `styles.html`.
- Breakpoints do tema (`main.css`/`page-*.css`): divisor mobile × desktop = **767/768px**;
  tablet **1024/1025px**; também 991/992, 575 e 1920. Há cortes avulsos de componentes
  (395–1140). Variável CSS **não** funciona em `@media`.
- **Plataforma injeta**: `product`, `settings`, `store`, `pages`, `utils` (`utils.is_mobile` é
  decidido no servidor, pelo dispositivo) e helpers que devolvem HTML pronto:
  `productHelper.pricing()`, `.form()`, `.social()`, `.shipping()`. O texto desses helpers
  (ex.: "Produto indisponível", botão de compra) **não é editável por template**: só por CSS.

## Template: Twig

O motor é **Twig do PHP, versão antiga (< 1.24)**. Testado com snippets temporários:

| Funciona | Não funciona |
|---|---|
| `1..3`, `range()`, `is divisible by`, `is even`, `is defined`, `starts with`, `matches`, `in`, `?:` | `??` (use `\|default()` ou `?:`) |
| `for … else`, `loop.index`, `macro` + `import _self`, `verbatim`, `{% set x %}…{% endset %}`, `do` | `{% apply %}`, `{% with %}` |
| `slice`, `keys`, `batch`, `date`, `format`, `json_encode`, `sort`, `title`, `first`, `last`, `default`, `escape`, `max()` | filtro `column`; funções-seta (`x => …`) e `map`/`filter`/`reduce` com seta |
| `merge`, `join`, `replace`, `number_format`, `split` (já usados pelo tema) | `{% include 'snippets/x' %}` ("Template not found"; só `{% element %}` acha arquivos do tema) |

- **`{% element 'snippets/x' {'chave': valor} %}`** recebe parâmetros, mas tem **escopo
  isolado**: o filho **não vê** variáveis `set` no chamador (só globais da plataforma, como
  `product` e `settings`) e variáveis criadas no filho **não voltam**. Passe tudo por parâmetro.
- Erro de template **não derruba a página**: o servidor imprime no HTML um bloco
  `Erro no Template: View/Elements/<arquivo>.html … Erro: <mensagem> at line N` e segue
  renderizando. Para depurar: buscar `Erro no Template` no HTML da página.
- Comentário `{# #}` pode citar `{% else %}` sem efeito; mas a **estrutura** `{% if %}/{% else %}`
  ao editar: conferir sempre com o original (já se perdeu um `{% else %}` ao inserir bloco).
- **Como testar um recurso**: criar snippet novo (`POST` do asset), incluir temporariamente em
  `layouts/default.html` com `{% element %}`, ler o resultado no HTML do preview, e **restaurar
  o layout e apagar os testes** (`DELETE`). Um erro por vez: o servidor só reporta o primeiro por
  arquivo; pular a linha que quebra e repetir.
- Não testados: `extends`/`block`/`embed`, tag `filter` (equivalente antigo de `apply`).

## Como editar

**API do Studio** (`.../theme-installs/<themeId>/assets`, sempre com `?platform_source=bling`,
`Authorization: Bearer <token>` e **`Accept: application/json`** — sem ele retorna 406):

| Operação | Detalhe |
|---|---|
| Listar | `GET` devolve todos os assets (`id`, `path`); **`content` vem `null`** na listagem |
| Ler | `GET .../assets/<id>`: `.data.content` em **texto puro** para `.html` |
| Gravar | `PUT .../assets/<id>` com `{"content": "<base64 UTF-8>"}` |
| Criar | `POST` com `{"name","path","content"(base64)}` |
| Apagar | `DELETE .../assets/<id>` |

- **CSS/JS estáticos** não retornam conteúdo pela API: leia pela CDN
  `https://images.tcdn.com.br/files/<LOJA_ID>/themes/<N>/css/<arquivo>` (`<N>` = número da
  pasta do tema na CDN, **não** o `themeId`; descobrir pela URL de qualquer `asset()` renderizado).
  O `checksum` retornado no `PUT` fica desatualizado, mas o conteúdo da CDN atualiza.
- Base64 de UTF-8: codificar os bytes (`TextEncoder`), não `btoa(string)` direto, senão
  "content must be valid base64".
- **Editor de código (Monaco)** do Studio ignora digitação programática: editar **pela API**.
- **Editor visual** (`/studio-app/themes/<themeId>/editor`): cores persistem; o campo
  "Estilo Customizado" (CodeMirror) persiste; opções da seção "Geral"/selos **não persistem**
  (contornar por CSS/HTML). O seletor de fonte lista Google Fonts.
- **Verificar no preview**: página de obra, categoria, home e 1024px/390px. O navegador do
  agente só muda a viewport via `emulate` (`resize_page` não altera a largura).

## Convenções do projeto

- **Arquivo novo antes de editar original.** Tudo próprio em arquivos `${THEME_PREFIX}-*`
  (ex.: `css/${THEME_PREFIX}-extras.css`, `js/${THEME_PREFIX}-extras.js`). Arquivos originais
  só ganham o gancho mínimo (um `<link>`/`<script>`/`{% element %}`), comentado com
  `${THEME_MARK}:` para achar tudo com uma busca. Evita perder trabalho se o tema for atualizado.
- Classes próprias com prefixo `${THEME_PREFIX}-`. CSS próprio vai **depois** do CSS do tema
  em `styles.html`, e sobrescritas de classes do tema usam o mesmo seletor longo
  (`.product-wrapper .product-form ...`) para vencer a especificidade.
- Breakpoints novos: **767px** (mobile) e **1024px** (tablet), os do tema.
- O tema **fixa `text-align: left`** em vários blocos internos do form de produto; ao
  centralizar, listar os blocos (não basta `text-align` no pai).
- Peça indisponível: usar `product.available`, `product.stock`, `settings.without_stock_sale`
  e `product.upon_request` (sob consulta). O texto "Produto indisponível"/"Avise-me" vem de
  `productHelper.pricing()`: esconder por CSS quando houver aviso próprio.

## Produtos: no ERP → na loja

> Detalhes de API do ERP: ver [`api-docs/`](api-docs/). Aqui só o que liga ao catálogo da loja.

- Produto do ERP vai à loja pela tela **Produtos → "Exportar produtos multiloja"**
  (plataforma "Bling Loja Virtual"). **Antes**: categoria **da loja** (tela "Incluir categorias
  para selecionados" → escolher a loja → marcar categoria → "Incluir categoria aos produtos")
  e **peso > 0** (a Tray exige).
- Erros de exportação conhecidos: "Produto precisa ter uma categoria" (categoria da loja não
  gravada); "Produto possui um vínculo ativo que não foi encontrado" (vínculo falso, ver abaixo).
- **`POST /produtos/lojas`** cria vínculo, mas exige `idProdutoLoja` (id do produto na loja,
  campo `codigo` na resposta), que só existe **depois** da exportação. Inventar um valor cria
  vínculo falso que **bloqueia** a exportação; remover com `DELETE /produtos/lojas/<id>` e
  refazer pela tela. `GET /produtos/lojas?idProduto=<id>` mostra o vínculo (`codigo` = id na loja).
- Atualizar peso/dimensões: `GET /produtos/<id>`, alterar `pesoBruto`/`pesoLiquido`/`dimensoes`,
  `PUT`.
- **Excluir produto**: `PATCH /produtos/<id>/situacoes {"situacao":"E"}` e depois
  `DELETE /produtos/<id>` (o `DELETE` direto falha: "deve estar com situação excluído").
  Exige confirmação do usuário (regra do `AGENTS.md`). O produto pode seguir no catálogo da loja
  (página abre) até ser excluído **no painel da loja** (iframe, ação do usuário).
- Listagem por categoria e busca da vitrine demoram a indexar; o produto abre pelo endereço
  direto antes. Estoque zero some das listagens conforme configuração da loja (não confirmado).
- **Imagens**: com "Imagens armazenadas no Bling", a foto chega à loja em até ~1 h e é copiada
  para a CDN da Tray. Trocar a preferência "imagens armazenadas / URL externa" **desvincula** as
  fotos internas de todos os produtos (reverter não as traz de volta). `PUT /produtos` pode
  derrubar a foto interna; preferir a tela para imagens. Reexportar produto já ligado atualiza a
  foto, mas nem sempre a descrição.

## Não verificado

- O que a atualização do tema ("Nova versão disponível") faz com arquivos editados: sobrescreve,
  cria nova instalação ou pede confirmação. Não há documentação pública encontrada; a convenção
  de arquivos próprios existe por precaução.
- Linguagem do servidor: URLs `.php` e Twig sugerem PHP, mas os cabeçalhos (`nginx`, Azion) não
  confirmam.
- Versão exata do Twig (só se sabe que é anterior à 1.24).
