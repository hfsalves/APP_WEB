# PortoBreak — SEO técnico

Implementação local: 18 de setembro de 2026. Não inclui publicação em produção,
submissão ao Google Search Console ou uma garantia de indexação/posicionamento.

## Páginas públicas

- Catálogo, páginas de alojamento e documentos institucionais têm títulos e
  descrições em português, inglês, espanhol e francês.
- Cada versão usa uma URL canónica com idioma explícito. Datas, número de
  hóspedes, pesquisa, tracking e caminhos de regresso não entram nos metadados.
  A paginação do catálogo preserva o número da página.
- As ligações `hreflang` no HTML identificam as quatro versões e a versão
  portuguesa de referência (`x-default`). Não é necessária uma segunda cópia
  destas relações no sitemap.
- Open Graph/Twitter permitem pré-visualizações nas partilhas. Os dados
  estruturados descrevem apenas conteúdo público, sem inventar avaliações,
  preços, disponibilidade ou divulgar moradas exatas/coordenadas dos alojamentos.
- As descrições comerciais dos alojamentos continuam a vir dos campos de cada
  idioma já existentes na aplicação; se faltarem, mantém-se o fallback existente.
  O SEO técnico não substitui uma revisão editorial dessas traduções.

## Descoberta e exclusão

`/sitemap.xml` inclui o catálogo, os cinco documentos institucionais e todos os
alojamentos ativos/não fechados, em cada idioma. A consulta lê apenas IDs, sem
consultas de preços/fotos por alojamento, e não depende das datas disponíveis.
Não se publica um `lastmod` inventado. Uma falha da base de dados devolve 503,
em vez de um sitemap vazio com sucesso. O documento tem cache de cinco minutos.

`/robots.txt` no domínio público permite rastreio e identifica o sitemap. As
pesquisas filtradas recebem `noindex, follow`; conta, recuperação/validação de
email, reserva/pagamento, APIs e links pessoais recebem `noindex, nofollow`.
Cabeçalhos `X-Robots-Tag` também cobrem respostas sem o template comum e erros.
As rotas de hóspede `/r2` e `/api/r` no domínio PortoBreak ficam igualmente
excluídas. Não se bloqueiam estas páginas no robots.txt público: o motor tem de
poder ler a instrução de não indexação. Isso não substitui autenticação ou
autorizações, que mantêm os controlos existentes.

No ambiente local e em origens não públicas o portal recebe `noindex` e o
robots.txt não permite rastreio. A origem dos URLs canónicos/sitemap é fixa,
`PORTOBREAK_PUBLIC_BASE_URL` (por defeito `https://portobreak.com`), nunca derivada
do Host enviado pelo visitante. O domínio efetivo usado para decidir indexação
acompanha o encaminhamento por proxy da aplicação.

## Após publicação

1. Confirmar no HTTPS público que robots.txt e sitemap.xml respondem 200, sem
   login, e que o proxy não substitui estes ficheiros nem acrescenta `noindex`.
2. Verificar uma página de catálogo, um alojamento e as quatro versões de idioma;
   verificar também a exclusão de login, pagamento e links pessoais.
3. Adicionar/verificar a propriedade no Google Search Console e submeter
   `https://portobreak.com/sitemap.xml`. Esta operação externa não foi efetuada.
4. Rever cobertura, canónicas selecionadas, erros de rastreio e traduções em falta.
   A descoberta e indexação dependem do motor de pesquisa.

## Verificação local efetuada

- 25 testes SEO e 12 testes de cookies passaram; as seis verificações existentes
  de cancelamento também passaram.
- Pedidos HTTP ao Flask local, simulando `Host: portobreak.com` e os cabeçalhos
  do proxy, confirmaram robots, sitemap, páginas por idioma, paginação e exclusão
  das áreas privadas. Isto não representa uma verificação do servidor público.
- O inventário consultado produziu 416 URLs únicas: 98 alojamentos e seis páginas
  gerais, em quatro idiomas. Estes números variam com o catálogo.
- Sem alterações ao fluxo de pagamento, criação de reservas ou envio de emails.

## Referências oficiais

- [Google — versões localizadas](https://developers.google.com/search/docs/specialty/international/localized-versions)
- [Google — URLs canónicas](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls)
- [Google — robots.txt](https://developers.google.com/search/docs/crawling-indexing/robots/intro)
- [Google — construir e submeter sitemaps](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap)
