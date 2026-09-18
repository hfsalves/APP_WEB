# PortoBreak — documentos legais (2026-09-18.1)

Implementação local do ponto 1: Termos de Reserva, Política de Privacidade,
Política de Cookies e Informação Legal/Apoio ao Consumidor, em PT/EN/ES/FR.
Textos editáveis em `content/booking_portal/legal/*.json`; versão/data e identidade
centralizadas em `services/booking_portal_legal.py`. Após qualquer alteração
material aos textos, incrementar a versão e atualizar a data.

## Factos usados e verificações pendentes

- Identidade, NIF e morada reproduzem os dados já apresentados no rodapé.
  Confirmar a morada oficial, os dados de registo comercial, capital social,
  telefone público e se a GuestSpaTur é a parte contratante para todos os imóveis.
- `helpdesk@guestspa.pt` é uma caixa operacional já indicada pelo utilizador.
  Foi usada como contacto de apoio/privacidade nesta versão local; confirmar
  que a equipa gere pedidos dos titulares nessa caixa. Não foi designado um EPD.
- Livro de Reclamações: ligação ao portal oficial. Confirmar a inscrição da
  entidade e dos estabelecimentos, e eventual URL específica.
- CICAP: indicado com âmbito territorial/material e contactos oficiais.
  Não se afirma adesão voluntária da empresa. Confirmar a competência para os
  contratos concretos e eventual vinculação adicional.
- RNAL: passou a apresentar `AL.LICENCA` quando preenchido na listagem,
  detalhe e formulário. Verificar o preenchimento e a validade dos números
  de todos os alojamentos. Não é gerado qualquer número em falta.
- Conservação: o código não tem uma rotina de eliminação de dados `PB_*`.
  O texto apresenta critérios por finalidade, não promete apagamento automático
  nem inventa um prazo uniforme. Definir e operacionalizar uma tabela de retenção
  (pedidos incompletos, reservas, contas, comunicações, logs e cópias de segurança).
- Fornecedores e transferências: confirmar fornecedores de alojamento, email,
  backups, localizações, contratos e garantias concretas. As notificações internas
  seguem também para caixas Gmail e Hotmail por instrução do utilizador. Os
  textos identificam categorias e serviços conhecidos, sem afirmar que todo o
  tratamento ocorre no EEE ou que existem contratos verificados.
- Cookies: o inventário e as medidas deste ponto foram atualizados no ponto 2,
  descrito em `PORTOBREAK_COOKIE_AUDIT.md`. Existe agora escolha de preferências
  e mapas externos, com registo assinado durante 180 dias; a memorização do idioma
  depende da escolha. Fontes e Leaflet são locais, e o OpenStreetMap fica bloqueado
  até autorização. A auditoria de produção, CDN/proxy e checkout continua distinta
  da verificação local.
- O formulário mostra informação de privacidade e acesso aos termos junto ao
  botão de envio. A aceitação obrigatória/versionada do ponto 2 não faz parte
  desta alteração; a versão visível do documento não é prova de aceitação.
- Cancelamentos/reembolsos são descritos como pedidos à equipa. Esta alteração
  não implementa reembolsos automáticos nem altera o fluxo Stripe.

## Fontes consultadas

- RGPD, sobretudo artigos 6, 12, 13 e 44–49:
  https://eur-lex.europa.eu/eli/reg/2016/679/oj?locale=pt
- CNPD — consentimento e fundamento contratual:
  https://www.cnpd.pt/organizacoes/areas-tematicas/consentimento/
- CNPD — nota sobre cookies:
  https://www.cnpd.pt/media/x2zdus50/nota-informativa-cnpd_cookies_20210625.pdf
- Livre resolução, DL 24/2014, artigo 17.º, n.º 1, alínea k):
  https://diariodarepublica.pt/dr/legislacao-consolidada/decreto-lei/2014-73222992
- Identificação de AL, DL 128/2014, artigo 17.º:
  https://diariodarepublica.pt/dr/legislacao-consolidada/decreto-lei/2014-56917875
- Turismo de Portugal — Livro de Reclamações AL:
  https://business.turismodeportugal.pt/pt/Planear_Iniciar/Licenciamento_Registo_da_Atividade/Alojamento_Local/Paginas/livro-de-reclamacoes-eletronico-al.aspx
- CICAP: https://cicap.pt/
- Arbitragem de consumo: https://www.gov.pt/servicos/realizar-uma-arbitragem-de-conflitos-de-consumo-atraves-dos-centros-de-arbitragem-apoiados-pelo-ministerio-da-justica
- Encerramento da antiga plataforma ODR em 20/07/2025:
  https://consumer-redress.ec.europa.eu/site-relocation_en

Os documentos estão preparados para revisão local. A implementação não constitui
uma verificação integral de conformidade jurídica ou das práticas operacionais.
