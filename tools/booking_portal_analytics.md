# Analítica própria PortoBreak

Estado verificado em 21/09/2026: as cinco tabelas foram criadas na BD configurada;
inserções, idempotência, duração e ligação à reserva foram validadas numa transação
SQL Server integralmente revertida, sem dados de teste persistentes. O preview
local foi atualizado. O domínio público ainda servia a versão sem esta recolha:
é necessária a publicação do código para começar a receber dados reais.

## Ativação

1. Aplicar `migrations/booking_portal_analytics.sql` na BD de produção, ou chamar
   `services.booking_portal_analytics_store.ensure_schema(engine)` explicitamente.
   São criadas apenas cinco tabelas `PB_ANALYTICS_*` e os seus índices. Nenhuma
   tabela de clientes, reservas ou pagamentos é alterada. O runtime **não** cria
   tabelas durante pedidos HTTP.
2. Publicar os ficheiros deste conjunto e reiniciar/recarregar o processo Flask
   pelo procedimento habitual. A migração sozinha **não inicia a recolha**.
3. Por omissão a recolha está ativa apenas para o Host `portobreak.com` ou
   `www.portobreak.com`. `PORTOBREAK_ANALYTICS_ENABLED=false` desliga-a. O proxy
   deve preservar o Host público; não confiamos em X-Forwarded-Host arbitrário.
4. Para país estimado, confirmar que a Cloudflare envia `CF-IPCountry` e que o
   origin só aceita esse cabeçalho através de proxies confiáveis. Ligações
   diretas dos CIDRs públicos da Cloudflare são reconhecidas. Se existe Nginx
   ou cloudflared local, configurar `PORTOBREAK_ANALYTICS_TRUSTED_PROXY_CIDRS`
   com o endereço/CIDR exato **só depois de verificar a proteção do upstream**.
   Não configurar `0.0.0.0/0`, nem confiar em localhost apenas por conveniência.
   Sem esta confirmação o país fica `ZZ`/`unknown`, não é inferido do idioma.
5. Fazer uma visita controlada ao domínio público: antes de consentir só aumenta
   `TOTALS`; ao aceitar Analítica surgem `VISITORS`, `SESSIONS`, `PAGEVIEWS`.
   Ao retirar consentimento cessam os eventos e desaparecem os dois cookies.
   Validar POST `/reservas/analitica/eventos` com resposta 200 e os registos na BD.
   Esta visita de validação deve ser reconhecida como tráfego de teste no relatório.

`localhost`, IPs, backoffice e testes ficam excluídos por omissão. Para testes
isolados pode usar-se `PORTOBREAK_ANALYTICS_ALLOW_LOCAL=true`, **com uma BD de
teste**, nunca para acrescentar navegação de desenvolvimento às métricas reais.

## O que os números significam

- **Acessos**: pedidos HTTP 200 a páginas do portal e consultas de preço no mapa,
  agregados por hora UTC, tipo de página/alojamento, dispositivo, país estimado,
  domínio de origem, pesquisa presente e robô identificado. Não são pessoas,
  nem sessões, nem uma contagem garantida de todos os acessos (cache, falhas,
  aplicações de terceiros e bloqueios podem introduzir lacunas).
- **Visitante**: identificador aleatório de um navegador que consentiu. Outro
  dispositivo, remoção de cookies ou nova decisão podem contar novamente a mesma
  pessoa. Quem recusa não entra na contagem de visitantes únicos.
- **Sessão**: agrupa páginas consentidas até 30 minutos de inatividade observada.
  `started_at`/`last_seen_at` permitem duração observada; `active_seconds` é uma
  estimativa de atividade em primeiro plano, limitada a 60 segundos sem interação,
  sem contar tempo oculto nem somar integralmente separadores simultâneos.
- **Páginas/consultas**: `page_kind` separa catálogo, alojamento, formulário,
  resultado de pagamento e `map_quote` (popup; não é uma navegação de página).
  `search_json` contém só datas válidas, números de adultos/crianças/bebés e um
  indicador de pesquisa textual. O texto livre não é guardado. Repetições de
  pedidos HTTP contam nos agregados; os eventos browser são idempotentes por página.
- **Origem**: domínio do Referer e, com consentimento, `utm_source`, `utm_medium`,
  `utm_campaign` em formato restrito. Não se guardam parâmetros de pesquisa do
  motor, URLs completas, gclid/fbclid, `utm_term`, `utm_content` ou tokens privados.
  Referrer ausente significa **origem desconhecida**, não prova acesso direto.
  A primeira página medida depois do consentimento inicia a atribuição da sessão;
  não se reconstrói navegação anterior ao consentimento.
- **País**: localização aproximada da ligação estimada pela Cloudflare, não país
  de residência, origem pessoal ou nacionalidade. VPNs podem alterar o resultado.
- **Dispositivo/navegador/sistema**: famílias deduzidas do User-Agent, sem guardar
  o valor original. Identificação de robôs por padrões conhecidos é imperfeita;
  `is_bot=false` não garante uma pessoa.
- **Género/faixa etária**: colunas reservadas `NULL`, fonte `unknown`. Não há
  inferência por nome, país ou dispositivo, nem formulário demográfico ativo.
- **Conversão**: `CONVERSIONS.booking_id` liga o pedido submetido à sessão ativa
  consentida. Não significa pagamento concluído: o dashboard deverá cruzar o
  estado real de `PB_BOOKING_REQUESTS` e `PB_STRIPE_TEST_PAYMENTS`, distinguindo LIVE
  de TEST. Não duplica dados pessoais ou de cartões. Sem consentimento não há ligação.

## Consentimento e segurança

Categoria Analítica independente e inicialmente desmarcada, em PT/EN/ES/FR.
Versão `2026-09-21.1` exige nova decisão aos visitantes com consentimento antigo.
Rejeitar não impede reservas. Cookies aleatórios assinados HttpOnly/SameSite=Lax,
Secure no domínio público: `portobreak_visitor` até 180 dias e
`portobreak_analytics_session` até 30 minutos, ambos limitados ao consentimento.
Não há fingerprint, persistência de IPs completos, geolocalização GPS, pixels de
terceiros, conteúdo de formulários ou inferência demográfica.

O endpoint exige consentimento válido, origem correspondente, contexto assinado,
payload limitado a 8 KiB, allowlist de campos, propriedade da página/sessão e
limites de eventos. O rate limit é por processo e serve como proteção básica,
não substitui proteção contra abuso no proxy. Falhas de analítica não interrompem
reservas e são registadas sem parâmetros privados. Não existe API pública de leitura.

## Retenção

- Sessões, páginas e ligações a reservas: 90 dias.
- Identificadores aleatórios de visitantes inativos e agregados: 180 dias.
- Limpeza best-effort acionada pelo tráfego, no máximo uma vez por hora/processo;
  quando o portal está parado a limpeza só corre quando voltam os acessos.
  Para retenção estritamente calendarizada, executar `store.prune(engine, now)`
  diariamente no agendador operacional existente (não é criado automaticamente).
- A limpeza só remove dados destas tabelas novas, nunca reservas ou pagamentos.

## Verificação

```sh
.venv/bin/python -m unittest discover -s tests -p 'test_booking_portal*.py' -q
node --test tests/booking_*.test.js
```

Os testes usam SQLite isolado/mocks e não precisam de importar `app.py` nem ligar
à BD real. O dashboard fica para uma fase seguinte.

Referências: [CNPD — cookies de analítica e consentimento](https://www.cnpd.pt/media/x2zdus50/nota-informativa-cnpd_cookies_20210625.pdf),
[Cloudflare — país estimado por IP](https://developers.cloudflare.com/network/ip-geolocation/).
Os textos de privacidade implementam esta minimização, mas não substituem revisão
jurídica da organização sobre finalidades, fundamento dos agregados e conservação.
