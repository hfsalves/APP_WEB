# PortoBreak — cookies e conteúdos externos

Data: 18 de setembro de 2026. Âmbito: implementação local do portal público
`/reservas`, incluindo páginas de conta, reserva e documentos legais. Este
inventário atualiza o ponto «Cookies» das notas `PORTOBREAK_LEGAL_REVIEW.md`.
Não é uma auditoria do ambiente de produção nem do backoffice da aplicação.

## Inventário e decisões de implementação

| Elemento | Categoria e finalidade | Comportamento e duração |
| --- | --- | --- |
| Cookie de sessão Flask (nome da configuração, por defeito `session`) | Necessário às funcionalidades usadas: sessão, conta e autorização para consultar pagamento | Mantém o funcionamento existente; sessão do navegador, com a ressalva de restauro de sessões pelo navegador. |
| `portobreak_privacy` | Necessário para guardar e respeitar a decisão sobre opcionais, incluindo rejeição | Registo assinado, `HttpOnly`, com versão, data da decisão, expiração e escolhas `preferences`/`external_maps`. Dura 180 dias desde a decisão; visitas não renovam o prazo. Não contém identificador de conta nem dados da reserva. |
| `portobreak_lang` | Preferências opcionais: recordar idioma | Só é lido/escrito com autorização válida para preferências. Até 365 dias; escrita ou mudança de idioma inicia o prazo. Não é renovado a cada visita. É eliminado ao recusar/desativar preferências ou quando a autorização deixa de ser válida. |
| Imagens de mapas em `tile.openstreetmap.org` | Conteúdo externo opcional | Pedidos bloqueados até autorizar mapas; permissão independente do idioma. A revogação remove os mapas da página e impede novos pedidos iniciados pela aplicação. Não desfaz pedidos já enviados. |
| Inter e Leaflet | Recursos estáticos servidos pelo portal | Ficheiros alojados localmente. Não requerem carregamento de Google Fonts ou unpkg no portal. |
| Imagens de alojamentos em `szeroapp.com/static/` | Conteúdo da operação do portal | Pedidos de imagens mantidos; envolvem dados técnicos de entrega, como IP. O domínio externo é divulgado na política. Não se presume ausência de cabeçalhos/cookies adicionados em produção. |
| Stripe Checkout alojado | Ambiente separado de pagamento | Não é carregado pelo gestor de cookies do portal. As escolhas no portal não configuram as opções ou cookies da Stripe; ligação à política do prestador. |

Não foram identificadas integrações de Google Analytics, Meta Pixel, publicidade
ou outro serviço de analítica nos componentes do portal analisados. O painel não
apresenta opções para serviços inexistentes.

## Escolhas do visitante

- Primeira visita: aceitar opcionais, recusar opcionais ou configurar. Preferências
  e mapas começam desativados; a navegação e a reserva continuam disponíveis.
- Aceitar e recusar devem ter a mesma acessibilidade e destaque no aviso.
- «Gerir cookies» no rodapé permite alterar ou retirar a escolha; cookies
  necessários são informativos e não têm interruptor de desativação no painel.
- O parâmetro de idioma na URL continua funcional quando o idioma persistente
  é recusado. Uma escolha guardada não é condição para pesquisar ou reservar.
- Expiração, assinatura inválida ou versão de consentimento desatualizada levam
  a opcionais desativados e a novo pedido de escolha.
- A decisão é guardada no cookie assinado do navegador. Não foi criado um
  histórico central de consentimentos em base de dados. Não deve ser descrita
  como prova de aceitação dos Termos de Reserva.

## Documentação e verificação

As políticas de Cookies e Privacidade em PT/EN/ES/FR acompanham este comportamento.
A versão dos documentos legais e a versão do consentimento são controlos
distintos: alterar finalidades ou fornecedores opcionais exige rever o aviso,
o bloqueio prévio, os textos e a versão de consentimento.

A validação técnica local deve abranger uma visita sem cookies, recusa,
aceitação, escolhas por categoria, recarregamento, troca de idioma, revogação
com mapas abertos e registos inválidos/expirados. Nos pedidos de rede, confirmar
ausência de Google Fonts/unpkg e de imagens OSM antes da autorização. Estes
cenários não implicam efetuar pagamentos ou reservas reais.

Antes de publicação, verificar em navegador limpo o domínio HTTPS público e
eventuais cabeçalhos introduzidos pelo proxy/CDN, as respostas das imagens de
`szeroapp.com` e o percurso separado da Stripe. Os cookies próprios novos usam
`SameSite=Lax`, `HttpOnly` e `Secure` em HTTPS/no domínio público; a sessão
existente e as configurações do alojamento também devem ser conferidas nesse
ambiente. A presente nota não afirma conformidade integral de produção.

## Fontes oficiais consultadas

- [CNPD — nota sobre cookies](https://www.cnpd.pt/media/x2zdus50/nota-informativa-cnpd_cookies_20210625.pdf):
  responsabilidade do operador, dever de informação e consentimento quando
  exigido, incluindo analítica.
- [EDPB — Orientações 05/2020 sobre consentimento](https://www.edpb.europa.eu/documents/guideline/guidelines-052020-on-consent-under-regulation-2016679_en):
  escolha livre, específica e informada, ação afirmativa e possibilidade de
  retirada. As categorias separadas e o bloqueio anterior à decisão concretizam
  estas opções no portal.
- [OpenStreetMap Foundation — Privacy Policy](https://osmfoundation.org/wiki/Privacy_Policy):
  os serviços de mapas podem registar IP, informação do navegador/dispositivo e
  utilização. Autorizar mapas não equivale a afirmar que apenas existem cookies.
- [Stripe — Cookie Policy](https://stripe.com/legal/cookies-policy):
  cookies e tecnologias da Stripe têm informação própria no respetivo ambiente.

Os prazos de 180 e 365 dias são escolhas desta implementação, não prazos mínimos
ou máximos legais deduzidos destas fontes.
