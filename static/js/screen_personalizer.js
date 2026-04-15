document.addEventListener('DOMContentLoaded', () => {
  const cfg = window.SCREEN_PERSONALIZER_CONFIG || {};
  const els = {
    layout: document.getElementById('spvLayout'),
    sidebar: document.getElementById('spvSidebar'),
    pageSubtitle: document.getElementById('spvPageSubtitle'),
    screenSelect: document.getElementById('spvScreenSelect'),
    formModeBtn: document.getElementById('spvFormModeBtn'),
    listModeBtn: document.getElementById('spvListModeBtn'),
    desktopModeBtn: document.getElementById('spvDesktopModeBtn'),
    mobileModeBtn: document.getElementById('spvMobileModeBtn'),
    exactWidthsBtn: document.getElementById('spvExactWidthsBtn'),
    proportionalWidthsBtn: document.getElementById('spvProportionalWidthsBtn'),
    sidebarTitle: document.getElementById('spvSidebarTitle'),
    sidebarFieldsBtn: document.getElementById('spvSidebarFieldsBtn'),
    sidebarObjectsBtn: document.getElementById('spvSidebarObjectsBtn'),
    sidebarVariablesBtn: document.getElementById('spvSidebarVariablesBtn'),
    sidebarAddBtn: document.getElementById('spvSidebarAddBtn'),
    sidebarCollapseBtn: document.getElementById('spvSidebarCollapseBtn'),
    sidebarBody: document.getElementById('spvSidebarBody'),
    fieldsList: document.getElementById('spvFieldsList'),
    propertiesContent: document.getElementById('spvPropertiesContent'),
    previewEmpty: document.getElementById('spvPreviewEmpty'),
    previewStage: document.getElementById('spvPreviewStage'),
    previewScale: document.getElementById('spvPreviewScale'),
    status: document.getElementById('spvStatus'),
    saveBtn: document.getElementById('spvSaveBtn'),
    cancelBtn: document.getElementById('spvCancelBtn'),
    backBtn: document.getElementById('spvBackBtn'),
    variableModal: document.getElementById('spvVariableModal'),
    variableForm: document.getElementById('spvVariableForm'),
    variableModalTitle: document.getElementById('spvVariableModalTitle'),
    variableStamp: document.getElementById('spvVariableStamp'),
    variableName: document.getElementById('spvVariableName'),
    variableDescription: document.getElementById('spvVariableDescription'),
    variableType: document.getElementById('spvVariableType'),
    variableDefault: document.getElementById('spvVariableDefault'),
    variableDefaultHint: document.getElementById('spvVariableDefaultHint'),
    variableHelp: document.getElementById('spvVariableHelp'),
    variableDeleteBtn: document.getElementById('spvVariableDeleteBtn'),
    variableSaveBtn: document.getElementById('spvVariableSaveBtn'),
    eventEditorModal: document.getElementById('spvEventEditorModal'),
    eventEditorTitle: document.getElementById('spvEventEditorTitle'),
    eventEditorContext: document.getElementById('spvEventEditorContext'),
    eventEditorLegacy: document.getElementById('spvEventEditorLegacy'),
    eventToolbox: document.getElementById('spvEventToolbox'),
    eventBuilder: document.getElementById('spvEventBuilder'),
    eventConfig: document.getElementById('spvEventConfig'),
    eventCode: document.getElementById('spvEventCode'),
    eventClearBtn: document.getElementById('spvEventClearBtn'),
    eventSaveBtn: document.getElementById('spvEventSaveBtn'),
  };

  const state = {
    screens: [],
    sqlTables: [],
    selectedMenustamp: String(cfg.initialMenustamp || '').trim(),
    detail: null,
    loading: false,
    saving: false,
    resize: null,
    drag: null,
    selectedScope: 'field',
    selectedFieldStamp: '',
    useExactWidths: true,
    layoutMode: 'form',
    viewportMode: 'desktop',
    suppressPreviewClickUntil: 0,
    sidebarMode: 'fields',
    sidebarCollapsed: false,
    customObjects: [],
    variables: [],
    customObjectSeq: 0,
    selectedVariableStamp: '',
    eventLineSeq: 0,
    eventEditor: null,
    eventDrag: null,
    eventToolboxOpenGroup: 'flow',
  };

  const TYPE_META = {
    TEXT: { icon: 'fa-solid fa-i-cursor', label: 'Texto' },
    COMBO: { icon: 'fa-solid fa-square-caret-down', label: 'Combo' },
    DATE: { icon: 'fa-solid fa-calendar-day', label: 'Data' },
    HOUR: { icon: 'fa-solid fa-clock', label: 'Hora' },
    INT: { icon: 'fa-solid fa-hashtag', label: 'Inteiro' },
    DECIMAL: { icon: 'fa-solid fa-calculator', label: 'Decimal' },
    MEMO: { icon: 'fa-solid fa-align-left', label: 'Memo' },
    BIT: { icon: 'fa-solid fa-square-check', label: 'Bit' },
    BUTTON: { icon: 'fa-solid fa-square', label: 'Botao' },
    TABLE: { icon: 'fa-solid fa-table', label: 'Tabela' },
    COLOR: { icon: 'fa-solid fa-palette', label: 'Cor' },
    LINK: { icon: 'fa-solid fa-link', label: 'Link' },
    SPACE: { icon: 'fa-solid fa-left-right', label: 'Espaço' },
  };
  const TYPE_LABELS_EN = {
    TEXT: 'Text',
    COMBO: 'Combo',
    DATE: 'Date',
    HOUR: 'Time',
    INT: 'Integer',
    DECIMAL: 'Decimal',
    MEMO: 'Memo',
    BIT: 'Checkbox',
    BUTTON: 'Button',
    TABLE: 'Table',
    COLOR: 'Color',
    LINK: 'Link',
    SPACE: 'Spacer',
    BOOL: 'Boolean',
    JSON: 'JSON',
  };
  const OBJECT_LIBRARY = [
    { id: 'TEXT', icon: TYPE_META.TEXT.icon, label: 'Text Field', key: 'TEXT' },
    { id: 'COMBO', icon: TYPE_META.COMBO.icon, label: 'Combo Box', key: 'COMBO' },
    { id: 'DATE', icon: TYPE_META.DATE.icon, label: 'Date Picker', key: 'DATE' },
    { id: 'HOUR', icon: TYPE_META.HOUR.icon, label: 'Time Field', key: 'HOUR' },
    { id: 'INT', icon: TYPE_META.INT.icon, label: 'Integer', key: 'INT' },
    { id: 'DECIMAL', icon: TYPE_META.DECIMAL.icon, label: 'Decimal', key: 'DECIMAL' },
    { id: 'MEMO', icon: TYPE_META.MEMO.icon, label: 'Memo', key: 'MEMO' },
    { id: 'BIT', icon: TYPE_META.BIT.icon, label: 'Checkbox', key: 'BIT' },
    { id: 'BUTTON', icon: TYPE_META.BUTTON.icon, label: 'Button', key: 'BUTTON' },
    { id: 'TABLE', icon: TYPE_META.TABLE.icon, label: 'Table', key: 'TABLE' },
    { id: 'COLOR', icon: TYPE_META.COLOR.icon, label: 'Color', key: 'COLOR' },
    { id: 'LINK', icon: TYPE_META.LINK.icon, label: 'Link', key: 'LINK' },
    { id: 'SPACE', icon: TYPE_META.SPACE.icon, label: 'Spacer', key: 'SPACE' },
  ];
  const VARIABLE_META = {
    TEXT: { icon: 'fa-solid fa-font', label: 'Text', hint: 'Valor livre em texto simples.' },
    MEMO: { icon: 'fa-solid fa-align-left', label: 'Long Text', hint: 'Texto longo, notas ou blocos multi-linha.' },
    INT: { icon: 'fa-solid fa-hashtag', label: 'Integer', hint: 'Numero inteiro, sem casas decimais.' },
    DECIMAL: { icon: 'fa-solid fa-calculator', label: 'Decimal', hint: 'Numero decimal. Aceita ponto ou virgula.' },
    DATE: { icon: 'fa-solid fa-calendar-day', label: 'Date', hint: 'Data em formato ISO, por exemplo 2026-04-07.' },
    BOOL: { icon: 'fa-solid fa-toggle-on', label: 'Boolean', hint: 'Use 1/0, true/false ou yes/no.' },
    JSON: { icon: 'fa-solid fa-code', label: 'JSON', hint: 'Estrutura JSON para configuracoes mais ricas.' },
  };
  const VARIABLE_TYPES = Object.keys(VARIABLE_META);
  const PREVIEW_GRID_UNITS = 100;
  const PREVIEW_GRID_UNITS_MOBILE = 40;
  const EVENT_OUTPUT_FIELD = { key: 'store_as', label: 'Guardar em variavel', type: 'text', placeholder: 'Ex: RESULTADO' };
  const EVENT_GROUP_LABELS = {
    flow: 'Flow',
    data: 'Data',
    operations: 'Operations',
    ui: 'UI',
    context: 'Context & Integration',
    screen_data: 'Screen Data',
  };
  const EVENT_COMMAND_LABELS = {
    START: 'Start',
    IF: 'If',
    ELSE: 'Else',
    RETURN: 'Return',
    FOR_EACH: 'For Each',
    WHILE: 'While',
    BREAK: 'Break',
    CONTINUE: 'Continue',
    DELAY: 'Delay',
    DEFINE_VARIABLE: 'Define Variable',
    GET_VALUE: 'Get Value',
    SET_VALUE: 'Set Value',
    COPY_VALUE: 'Copy Value',
    CREATE_OBJECT: 'Create Object',
    CREATE_LIST: 'Create List',
    ADD_TO_LIST: 'Add To List',
    GET_ITEM: 'Get Item',
    COUNT: 'Count',
    IS_EMPTY: 'Is Empty',
    CURSOR_NEW: 'Cursor New',
    CURSOR_RECCOUNT: 'Cursor RecCount',
    CURSOR_SCAN: 'Cursor Scan',
    CURSOR_APPEND: 'Cursor Append',
    CURSOR_DELETE: 'Cursor Delete',
    CURSOR_REPLACE: 'Cursor Replace',
    CURSOR_CLOSE: 'Cursor Close',
    EQUALS: 'Equals',
    NOT_EQUALS: 'Not Equals',
    GREATER: 'Greater',
    LESS: 'Less',
    AND: 'And',
    OR: 'Or',
    NOT: 'Not',
    SUM: 'Sum',
    SUBTRACT: 'Subtract',
    MULTIPLY: 'Multiply',
    DIVIDE: 'Divide',
    ROUND: 'Round',
    CONCAT: 'Concat',
    SUBSTRING: 'Substring',
    TRIM: 'Trim',
    UPPER: 'Upper',
    LOWER: 'Lower',
    DATE_ADD: 'Date Add',
    DATE_DIFF: 'Date Diff',
    MESSAGE: 'Message',
    CONFIRM: 'Confirm',
    INPUT_BOX: 'InputBox',
    OPEN_MODAL: 'Open Modal',
    CLOSE_MODAL: 'Close Modal',
    FOCUS_FIELD: 'Focus Field',
    SHOW_HIDE: 'Show/Hide',
    ENABLE_DISABLE: 'Enable/Disable',
    SET_REQUIRED: 'Set Required',
    REFRESH_SCREEN: 'Refresh Screen',
    REFRESH_GRID: 'Refresh Grid',
    GET_SYSTEM_VALUE: 'Get System Value',
    CALL_API: 'Call API',
    GET_API_VALUE: 'Get API Value',
    CALL_SCREEN_ACTION: 'Call Screen Action',
    EMIT_EVENT: 'Emit Event',
    LOG_DEBUG: 'Log Debug',
    GET_FIELD: 'Get Field',
    SET_FIELD: 'Set Field',
    GET_ROW: 'Get Row',
    SET_ROW: 'Set Row',
    GET_SELECTED_ROWS: 'Get Selected Rows',
    VALIDATE_FIELD: 'Validate Field',
    VALIDATE_FORM: 'Validate Form',
    ENDIF: 'EndIf',
    ENDWHILE: 'EndWhile',
    ENDFOR: 'EndFor',
    ENDCURSOR_SCAN: 'EndScan',
  };
  const EVENT_FIELD_LABELS = {
    store_as: 'Store As',
    condition: 'Condition',
    value: 'Value',
    item_name: 'Item',
    source: 'Source',
    duration_ms: 'Duration',
    name: 'Name',
    default_value: 'Default',
    target: 'Target',
    list_name: 'List',
    index: 'Index',
    left: 'Left',
    right: 'Right',
    decimals: 'Decimals',
    date_value: 'Date',
    delta: 'Delta',
    message: 'Message',
    prompt: 'Prompt',
    modal_name: 'Modal',
    field_name: 'Field',
    mode: 'Mode',
    grid_name: 'Grid',
    system_key: 'Key',
    method: 'Method',
    path: 'Path',
    action_name: 'Action',
    event_name: 'Event',
    row_ref: 'Row',
    row_name: 'Row As',
    date_start: 'Date A',
    date_end: 'Date B',
    start: 'Start',
    length: 'Length',
    cursor_name: 'Cursor',
    cursor_mode: 'Mode',
    cursor_fields: 'Fields',
    sql_query: 'SQL Query',
    field_name: 'Field',
  };
  const EVENT_CURSOR_FIELD_TYPES = [
    { value: 'TEXT', label: 'Text' },
    { value: 'MEMO', label: 'Long Text' },
    { value: 'INT', label: 'Integer' },
    { value: 'DECIMAL', label: 'Decimal' },
    { value: 'DATE', label: 'Date' },
    { value: 'BOOL', label: 'Boolean' },
    { value: 'JSON', label: 'JSON' },
  ];
  const EVENT_COMMAND_GROUPS = [
    {
      id: 'flow',
      label: 'Fluxo',
      items: [
        { id: 'START', label: 'Start', description: 'Marca o inicio do algoritmo.', fields: [] },
        { id: 'IF', label: 'If', description: 'Cria um bloco IF / ELSE / ENDIF.', template: 'if', fields: [{ key: 'condition', label: 'Condicao', type: 'textarea', rows: 3, placeholder: 'Ex: Get Field("ESTADO") Equals "Fechado"' }] },
        { id: 'ELSE', label: 'Else', description: 'Adiciona um bloco alternativo.', template: 'else', fields: [] },
        { id: 'RETURN', label: 'Return', description: 'Termina o fluxo e devolve um valor.', fields: [{ key: 'value', label: 'Valor', type: 'text', placeholder: 'Ex: true' }] },
        { id: 'FOR_EACH', label: 'For Each', description: 'Percorre uma lista ou colecao.', template: 'for_each', fields: [{ key: 'item_name', label: 'Item', type: 'text', placeholder: 'Ex: linha' }, { key: 'source', label: 'Lista', type: 'text', placeholder: 'Ex: LINHAS_SELECIONADAS' }] },
        { id: 'WHILE', label: 'While', description: 'Repete enquanto a condicao for verdadeira.', template: 'while', fields: [{ key: 'condition', label: 'Condicao', type: 'textarea', rows: 3, placeholder: 'Ex: CONTADOR Less 10' }] },
        { id: 'BREAK', label: 'Break', description: 'Sai do ciclo atual.', fields: [] },
        { id: 'CONTINUE', label: 'Continue', description: 'Salta para a proxima iteracao.', fields: [] },
        { id: 'DELAY', label: 'Delay', description: 'Espera alguns milissegundos.', fields: [{ key: 'duration_ms', label: 'Duracao (ms)', type: 'number', min: '0', step: '100', placeholder: 'Ex: 500' }] },
      ],
    },
    {
      id: 'data',
      label: 'Dados',
      items: [
        { id: 'DEFINE_VARIABLE', label: 'Definir variavel', description: 'Declara uma variavel local.', fields: [{ key: 'name', label: 'Nome', type: 'text', placeholder: 'Ex: TOTAL' }, { key: 'default_value', label: 'Default', type: 'text', placeholder: 'Ex: 0' }] },
        { id: 'GET_VALUE', label: 'Get Value', description: 'Le um valor de uma origem.', fields: [{ key: 'source', label: 'Origem', type: 'text', placeholder: 'Ex: RESPOSTA.total' }, EVENT_OUTPUT_FIELD] },
        { id: 'SET_VALUE', label: 'Set Value', description: 'Atribui um valor a uma variavel.', fields: [{ key: 'target', label: 'Destino', type: 'text', placeholder: 'Ex: TOTAL' }, { key: 'value', label: 'Valor', type: 'text', placeholder: 'Ex: 12' }] },
        { id: 'COPY_VALUE', label: 'Copiar valor', description: 'Copia de uma origem para um destino.', fields: [{ key: 'source', label: 'Origem', type: 'text', placeholder: 'Ex: CAMPO_A' }, { key: 'target', label: 'Destino', type: 'text', placeholder: 'Ex: CAMPO_B' }] },
        { id: 'CREATE_OBJECT', label: 'Criar objeto', description: 'Cria uma estrutura objeto.', fields: [{ key: 'name', label: 'Nome', type: 'text', placeholder: 'Ex: payload' }] },
        { id: 'CREATE_LIST', label: 'Criar lista', description: 'Cria uma lista vazia.', fields: [{ key: 'name', label: 'Nome', type: 'text', placeholder: 'Ex: linhas' }] },
        { id: 'ADD_TO_LIST', label: 'Adicionar a lista', description: 'Adiciona um item a uma lista.', fields: [{ key: 'list_name', label: 'Lista', type: 'text', placeholder: 'Ex: linhas' }, { key: 'value', label: 'Valor', type: 'text', placeholder: 'Ex: REGISTO' }] },
        { id: 'GET_ITEM', label: 'Obter item', description: 'Le um item da lista.', fields: [{ key: 'list_name', label: 'Lista', type: 'text', placeholder: 'Ex: linhas' }, { key: 'index', label: 'Indice', type: 'text', placeholder: 'Ex: 0' }, EVENT_OUTPUT_FIELD] },
        { id: 'COUNT', label: 'Contar', description: 'Conta elementos.', fields: [{ key: 'source', label: 'Origem', type: 'text', placeholder: 'Ex: linhas' }, EVENT_OUTPUT_FIELD] },
        { id: 'IS_EMPTY', label: 'Is Empty', description: 'Verifica se esta vazio.', fields: [{ key: 'source', label: 'Origem', type: 'text', placeholder: 'Ex: linhas' }, EVENT_OUTPUT_FIELD] },
        {
          id: 'CURSOR_NEW',
          label: 'Cursor New',
          description: 'Cria um cursor vazio manual ou a partir de SQL.',
          fields: [
            { key: 'cursor_name', label: 'Cursor', type: 'text', placeholder: 'Ex: CUR_ACESSOS' },
            {
              key: 'cursor_mode',
              label: 'Mode',
              type: 'select',
              options: [
                { value: 'manual', label: 'Manual' },
                { value: 'sql', label: 'SQL Query' },
              ],
            },
            {
              key: 'cursor_fields',
              label: 'Fields',
              type: 'cursor_fields',
              showWhen: { cursor_mode: 'manual' },
            },
            {
              key: 'sql_query',
              label: 'SQL Query',
              type: 'textarea',
              rows: 6,
              placeholder: 'SELECT A, B FROM TABELA WHERE CHAVE = {{RECORD_STAMP}}',
              showWhen: { cursor_mode: 'sql' },
            },
          ],
        },
        { id: 'CURSOR_RECCOUNT', label: 'Cursor RecCount', description: 'Conta os registos do cursor.', fields: [{ key: 'cursor_name', label: 'Cursor', type: 'text', placeholder: 'Ex: CUR_ACESSOS' }, EVENT_OUTPUT_FIELD] },
        { id: 'CURSOR_SCAN', label: 'Cursor Scan', description: 'Percorre todas as linhas do cursor.', template: 'cursor_scan', fields: [{ key: 'cursor_name', label: 'Cursor', type: 'text', placeholder: 'Ex: CUR_ACESSOS' }, { key: 'row_name', label: 'Row As', type: 'text', placeholder: 'Ex: CUR_LINHA' }] },
        { id: 'CURSOR_APPEND', label: 'Cursor Append', description: 'Adiciona uma nova linha ao cursor.', fields: [{ key: 'cursor_name', label: 'Cursor', type: 'text', placeholder: 'Ex: CUR_ACESSOS' }, { key: 'value', label: 'Value', type: 'text', placeholder: 'Ex: {\"NOME\":\"Ana\"}' }, EVENT_OUTPUT_FIELD] },
        { id: 'CURSOR_DELETE', label: 'Cursor Delete', description: 'Remove uma linha do cursor.', fields: [{ key: 'cursor_name', label: 'Cursor', type: 'text', placeholder: 'Ex: CUR_ACESSOS' }, { key: 'row_ref', label: 'Row', type: 'text', placeholder: 'Blank = current scan row' }] },
        { id: 'CURSOR_REPLACE', label: 'Cursor Replace', description: 'Altera um campo de uma linha do cursor.', fields: [{ key: 'cursor_name', label: 'Cursor', type: 'text', placeholder: 'Ex: CUR_ACESSOS' }, { key: 'field_name', label: 'Field', type: 'text', placeholder: 'Ex: NOME' }, { key: 'value', label: 'Value', type: 'text', placeholder: 'Ex: Maria' }, { key: 'row_ref', label: 'Row', type: 'text', placeholder: 'Blank = current scan row' }] },
        { id: 'CURSOR_CLOSE', label: 'Cursor Close', description: 'Fecha e remove o cursor do runtime.', fields: [{ key: 'cursor_name', label: 'Cursor', type: 'text', placeholder: 'Ex: CUR_ACESSOS' }] },
      ],
    },
    {
      id: 'operations',
      label: 'Operacoes',
      items: [
        { id: 'EQUALS', label: 'Equals', description: 'Compara dois valores.', fields: [{ key: 'left', label: 'A', type: 'text', placeholder: 'Ex: VALOR1' }, { key: 'right', label: 'B', type: 'text', placeholder: 'Ex: VALOR2' }, EVENT_OUTPUT_FIELD] },
        { id: 'NOT_EQUALS', label: 'Not Equals', description: 'Compara desigualdade.', fields: [{ key: 'left', label: 'A', type: 'text', placeholder: 'Ex: VALOR1' }, { key: 'right', label: 'B', type: 'text', placeholder: 'Ex: VALOR2' }, EVENT_OUTPUT_FIELD] },
        { id: 'GREATER', label: 'Greater', description: 'Compara maior que.', fields: [{ key: 'left', label: 'A', type: 'text', placeholder: 'Ex: TOTAL' }, { key: 'right', label: 'B', type: 'text', placeholder: 'Ex: 0' }, EVENT_OUTPUT_FIELD] },
        { id: 'LESS', label: 'Less', description: 'Compara menor que.', fields: [{ key: 'left', label: 'A', type: 'text', placeholder: 'Ex: TOTAL' }, { key: 'right', label: 'B', type: 'text', placeholder: 'Ex: 0' }, EVENT_OUTPUT_FIELD] },
        { id: 'AND', label: 'And', description: 'Conjuncao logica.', fields: [{ key: 'left', label: 'A', type: 'text', placeholder: 'Ex: COND_1' }, { key: 'right', label: 'B', type: 'text', placeholder: 'Ex: COND_2' }, EVENT_OUTPUT_FIELD] },
        { id: 'OR', label: 'Or', description: 'Disjuncao logica.', fields: [{ key: 'left', label: 'A', type: 'text', placeholder: 'Ex: COND_1' }, { key: 'right', label: 'B', type: 'text', placeholder: 'Ex: COND_2' }, EVENT_OUTPUT_FIELD] },
        { id: 'NOT', label: 'Not', description: 'Negacao logica.', fields: [{ key: 'value', label: 'Valor', type: 'text', placeholder: 'Ex: CONDICAO' }, EVENT_OUTPUT_FIELD] },
        { id: 'SUM', label: 'Sum', description: 'Soma dois valores.', fields: [{ key: 'left', label: 'A', type: 'text', placeholder: 'Ex: PRECO' }, { key: 'right', label: 'B', type: 'text', placeholder: 'Ex: IVA' }, EVENT_OUTPUT_FIELD] },
        { id: 'SUBTRACT', label: 'Subtract', description: 'Subtrai dois valores.', fields: [{ key: 'left', label: 'A', type: 'text', placeholder: 'Ex: TOTAL' }, { key: 'right', label: 'B', type: 'text', placeholder: 'Ex: DESCONTO' }, EVENT_OUTPUT_FIELD] },
        { id: 'MULTIPLY', label: 'Multiply', description: 'Multiplica dois valores.', fields: [{ key: 'left', label: 'A', type: 'text', placeholder: 'Ex: QUANTIDADE' }, { key: 'right', label: 'B', type: 'text', placeholder: 'Ex: PRECO' }, EVENT_OUTPUT_FIELD] },
        { id: 'DIVIDE', label: 'Divide', description: 'Divide dois valores.', fields: [{ key: 'left', label: 'A', type: 'text', placeholder: 'Ex: TOTAL' }, { key: 'right', label: 'B', type: 'text', placeholder: 'Ex: 2' }, EVENT_OUTPUT_FIELD] },
        { id: 'ROUND', label: 'Round', description: 'Arredonda um valor.', fields: [{ key: 'value', label: 'Valor', type: 'text', placeholder: 'Ex: TOTAL' }, { key: 'decimals', label: 'Decimais', type: 'number', min: '0', step: '1', placeholder: 'Ex: 2' }, EVENT_OUTPUT_FIELD] },
        { id: 'CONCAT', label: 'Concat', description: 'Concatena texto.', fields: [{ key: 'left', label: 'Texto A', type: 'text', placeholder: 'Ex: NOME' }, { key: 'right', label: 'Texto B', type: 'text', placeholder: 'Ex: SOBRENOME' }, EVENT_OUTPUT_FIELD] },
        { id: 'SUBSTRING', label: 'Substring', description: 'Extrai parte de um texto.', fields: [{ key: 'value', label: 'Texto', type: 'text', placeholder: 'Ex: CODIGO' }, { key: 'start', label: 'Inicio', type: 'text', placeholder: 'Ex: 0' }, { key: 'length', label: 'Comprimento', type: 'text', placeholder: 'Ex: 3' }, EVENT_OUTPUT_FIELD] },
        { id: 'TRIM', label: 'Trim', description: 'Remove espacos.', fields: [{ key: 'value', label: 'Texto', type: 'text', placeholder: 'Ex: NOME' }, EVENT_OUTPUT_FIELD] },
        { id: 'UPPER', label: 'Upper', description: 'Converte para maiusculas.', fields: [{ key: 'value', label: 'Texto', type: 'text', placeholder: 'Ex: NOME' }, EVENT_OUTPUT_FIELD] },
        { id: 'LOWER', label: 'Lower', description: 'Converte para minusculas.', fields: [{ key: 'value', label: 'Texto', type: 'text', placeholder: 'Ex: EMAIL' }, EVENT_OUTPUT_FIELD] },
        { id: 'DATE_ADD', label: 'Date Add', description: 'Adiciona tempo a uma data.', fields: [{ key: 'date_value', label: 'Data', type: 'text', placeholder: 'Ex: HOJE' }, { key: 'delta', label: 'Delta', type: 'text', placeholder: 'Ex: +5d' }, EVENT_OUTPUT_FIELD] },
        { id: 'DATE_DIFF', label: 'Date Diff', description: 'Calcula diferenca entre datas.', fields: [{ key: 'date_start', label: 'Data A', type: 'text', placeholder: 'Ex: DATA_INI' }, { key: 'date_end', label: 'Data B', type: 'text', placeholder: 'Ex: DATA_FIM' }, EVENT_OUTPUT_FIELD] },
      ],
    },
    {
      id: 'ui',
      label: 'UI',
      items: [
        { id: 'MESSAGE', label: 'Message', description: 'Mostra uma mensagem ao utilizador.', fields: [{ key: 'message', label: 'Mensagem', type: 'textarea', rows: 3, placeholder: 'Ex: Registo gravado com sucesso.' }] },
        { id: 'CONFIRM', label: 'Confirm', description: 'Pede confirmacao ao utilizador.', fields: [{ key: 'message', label: 'Pergunta', type: 'textarea', rows: 3, placeholder: 'Ex: Pretende continuar?' }, EVENT_OUTPUT_FIELD] },
        { id: 'INPUT_BOX', label: 'InputBox', description: 'Pede um valor ao utilizador.', fields: [{ key: 'prompt', label: 'Prompt', type: 'textarea', rows: 3, placeholder: 'Ex: Indique a observacao' }, { key: 'default_value', label: 'Default', type: 'text', placeholder: 'Ex: N/A' }, EVENT_OUTPUT_FIELD] },
        { id: 'OPEN_MODAL', label: 'Open Modal', description: 'Abre um modal.', fields: [{ key: 'modal_name', label: 'Modal', type: 'text', placeholder: 'Ex: detalhe_cliente' }] },
        { id: 'CLOSE_MODAL', label: 'Close Modal', description: 'Fecha um modal.', fields: [{ key: 'modal_name', label: 'Modal', type: 'text', placeholder: 'Ex: detalhe_cliente' }] },
        { id: 'FOCUS_FIELD', label: 'Focus Field', description: 'Coloca o foco num campo.', fields: [{ key: 'field_name', label: 'Campo', type: 'text', placeholder: 'Ex: NOME' }] },
        { id: 'SHOW_HIDE', label: 'Show/Hide', description: 'Mostra ou esconde um elemento.', fields: [{ key: 'target', label: 'Alvo', type: 'text', placeholder: 'Ex: BTN_ENVIAR' }, { key: 'mode', label: 'Modo', type: 'select', options: [{ value: 'show', label: 'Show' }, { value: 'hide', label: 'Hide' }] }] },
        { id: 'ENABLE_DISABLE', label: 'Enable/Disable', description: 'Ativa ou desativa um elemento.', fields: [{ key: 'target', label: 'Alvo', type: 'text', placeholder: 'Ex: PRECO' }, { key: 'mode', label: 'Modo', type: 'select', options: [{ value: 'enable', label: 'Enable' }, { value: 'disable', label: 'Disable' }] }] },
        { id: 'SET_REQUIRED', label: 'Set Required', description: 'Torna um campo obrigatorio ou opcional.', fields: [{ key: 'field_name', label: 'Campo', type: 'text', placeholder: 'Ex: EMAIL' }, { key: 'mode', label: 'Modo', type: 'select', options: [{ value: 'required', label: 'Required' }, { value: 'optional', label: 'Optional' }] }] },
        { id: 'REFRESH_SCREEN', label: 'Refresh Screen', description: 'Recarrega o ecrã atual.', fields: [] },
        { id: 'REFRESH_GRID', label: 'Refresh Grid', description: 'Atualiza uma grelha.', fields: [{ key: 'grid_name', label: 'Grid', type: 'text', placeholder: 'Ex: GRID_LINHAS' }] },
      ],
    },
    {
      id: 'context',
      label: 'Contexto & Integracao',
      items: [
        { id: 'GET_SYSTEM_VALUE', label: 'Get System Value', description: 'Le um valor do sistema.', fields: [{ key: 'system_key', label: 'Chave', type: 'text', placeholder: 'Ex: user, FEID, empresa' }, EVENT_OUTPUT_FIELD] },
        { id: 'CALL_API', label: 'Call API', description: 'Invoca uma API externa ou interna.', fields: [{ key: 'endpoint', label: 'Endpoint', type: 'text', placeholder: 'Ex: /api/clientes' }, { key: 'method', label: 'Metodo', type: 'select', options: [{ value: 'GET', label: 'GET' }, { value: 'POST', label: 'POST' }, { value: 'PUT', label: 'PUT' }, { value: 'DELETE', label: 'DELETE' }] }, EVENT_OUTPUT_FIELD] },
        { id: 'GET_API_VALUE', label: 'Get API Value', description: 'Extrai um valor da resposta da API.', fields: [{ key: 'path', label: 'Caminho', type: 'text', placeholder: 'Ex: data.total' }, EVENT_OUTPUT_FIELD] },
        { id: 'CALL_SCREEN_ACTION', label: 'Call Screen Action', description: 'Invoca uma acao do ecrã.', fields: [{ key: 'action_name', label: 'Acao', type: 'text', placeholder: 'Ex: refreshTotals' }] },
        { id: 'EMIT_EVENT', label: 'Emit Event', description: 'Emite um evento para outros componentes.', fields: [{ key: 'event_name', label: 'Evento', type: 'text', placeholder: 'Ex: linhas-alteradas' }] },
        { id: 'LOG_DEBUG', label: 'Log Debug', description: 'Escreve um registo de diagnostico.', fields: [{ key: 'message', label: 'Mensagem', type: 'textarea', rows: 3, placeholder: 'Ex: Valor recebido na validacao' }] },
      ],
    },
    {
      id: 'screen_data',
      label: 'Dados de Ecra',
      items: [
        { id: 'GET_FIELD', label: 'Get Field', description: 'Le o valor de um campo.', fields: [{ key: 'field_name', label: 'Campo', type: 'text', placeholder: 'Ex: NOME' }, EVENT_OUTPUT_FIELD] },
        { id: 'SET_FIELD', label: 'Set Field', description: 'Atribui um valor a um campo.', fields: [{ key: 'field_name', label: 'Campo', type: 'text', placeholder: 'Ex: NOME' }, { key: 'value', label: 'Valor', type: 'text', placeholder: 'Ex: CLIENTE_X' }] },
        { id: 'GET_ROW', label: 'Get Row', description: 'Le uma linha do contexto atual.', fields: [{ key: 'row_ref', label: 'Linha', type: 'text', placeholder: 'Ex: CURRENT_ROW' }, EVENT_OUTPUT_FIELD] },
        { id: 'SET_ROW', label: 'Set Row', description: 'Altera uma linha do contexto atual.', fields: [{ key: 'row_ref', label: 'Linha', type: 'text', placeholder: 'Ex: CURRENT_ROW' }, { key: 'value', label: 'Valor', type: 'text', placeholder: 'Ex: payload' }] },
        { id: 'GET_SELECTED_ROWS', label: 'Get Selected Rows', description: 'Obtem as linhas selecionadas.', fields: [{ key: 'grid_name', label: 'Grid', type: 'text', placeholder: 'Ex: GRID_LINHAS' }, EVENT_OUTPUT_FIELD] },
        { id: 'VALIDATE_FIELD', label: 'Validate Field', description: 'Valida um campo.', fields: [{ key: 'field_name', label: 'Campo', type: 'text', placeholder: 'Ex: EMAIL' }, EVENT_OUTPUT_FIELD] },
        { id: 'VALIDATE_FORM', label: 'Validate Form', description: 'Valida o formulario.', fields: [EVENT_OUTPUT_FIELD] },
      ],
    },
  ];
  const EVENT_HIDDEN_COMMANDS = [
    { id: 'ENDIF', label: 'EndIf', description: 'Fecha o bloco IF.', fields: [], hidden: true },
    { id: 'ENDWHILE', label: 'EndWhile', description: 'Fecha o bloco WHILE.', fields: [], hidden: true },
    { id: 'ENDFOR', label: 'EndFor', description: 'Fecha o bloco FOR EACH.', fields: [], hidden: true },
    { id: 'ENDCURSOR_SCAN', label: 'EndScan', description: 'Fecha o bloco Cursor Scan.', fields: [], hidden: true },
  ];
  const EVENT_COMMAND_META = [...EVENT_COMMAND_GROUPS.flatMap((group) => group.items.map((item) => ({
    ...item,
    groupId: group.id,
    groupLabel: group.label,
  }))), ...EVENT_HIDDEN_COMMANDS].reduce((acc, item) => {
    acc[item.id] = item;
    return acc;
  }, {});

  function isMobileMode() {
    return String(state.viewportMode || 'desktop') === 'mobile';
  }

  function isListLayoutMode() {
    return String(state.layoutMode || 'form') === 'list';
  }

  function getCurrentLayoutMode() {
    if (isListLayoutMode()) {
      return isMobileMode() ? 'list_mobile' : 'list';
    }
    return isMobileMode() ? 'mobile' : 'desktop';
  }

  function isListMobileLayoutMode() {
    return getCurrentLayoutMode() === 'list_mobile';
  }

  function getOrderFieldForMode(mode = 'desktop') {
    const normalizedMode = String(mode || '').trim().toLowerCase();
    if (normalizedMode === 'list_mobile') return 'ORDEM_LISTA_MOBILE';
    if (normalizedMode === 'list') return 'ORDEM_LISTA';
    return normalizedMode === 'mobile' ? 'ORDEM_MOBILE' : 'ORDEM';
  }

  function getWidthFieldForMode(mode = 'desktop') {
    const normalizedMode = String(mode || '').trim().toLowerCase();
    if (normalizedMode === 'list_mobile') return 'TAM_LISTA_MOBILE';
    if (normalizedMode === 'list') return 'TAM_LISTA';
    return normalizedMode === 'mobile' ? 'TAM_MOBILE' : 'TAM';
  }

  function getRowKeyForMode(mode = 'desktop') {
    const normalizedMode = String(mode || '').trim().toLowerCase();
    if (normalizedMode === 'list_mobile') return '_SPV_ROW_LIST_MOBILE';
    if (normalizedMode === 'list') return '_SPV_ROW_LIST';
    return normalizedMode === 'mobile' ? '_SPV_ROW_MOBILE' : '_SPV_ROW';
  }

  function getPosKeyForMode(mode = 'desktop') {
    const normalizedMode = String(mode || '').trim().toLowerCase();
    if (normalizedMode === 'list_mobile') return '_SPV_POS_LIST_MOBILE';
    if (normalizedMode === 'list') return '_SPV_POS_LIST';
    return normalizedMode === 'mobile' ? '_SPV_POS_MOBILE' : '_SPV_POS';
  }

  function getActiveOrderField() {
    return getOrderFieldForMode(getCurrentLayoutMode());
  }

  function getActiveWidthField() {
    return getWidthFieldForMode(getCurrentLayoutMode());
  }

  function getActiveRowKey() {
    return getRowKeyForMode(getCurrentLayoutMode());
  }

  function getActivePosKey() {
    return getPosKeyForMode(getCurrentLayoutMode());
  }

  function getPreviewGridUnits() {
    return isMobileMode() && state.useExactWidths ? PREVIEW_GRID_UNITS_MOBILE : PREVIEW_GRID_UNITS;
  }

  function nextCustomObjectStamp() {
    state.customObjectSeq += 1;
    return `SPVOBJ-${Date.now().toString(36)}${state.customObjectSeq.toString(36)}`.slice(0, 25);
  }

  function escapeHtml(value) {
    return String(value ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function showToast(message, type = 'success') {
    if (typeof window.showToast === 'function') {
      window.showToast(message, type);
      return;
    }
    window.alert(message);
  }

  async function confirmDelete(message) {
    if (typeof window.szConfirmDelete === 'function') {
      return window.szConfirmDelete(message);
    }
    if (typeof window.szConfirm === 'function') {
      return window.szConfirm(message, {
        title: 'Confirmar eliminação',
        intent: 'danger',
      });
    }
    return false;
  }

  async function fetchJson(url, options = {}) {
    const response = await fetch(url, options);
    const raw = await response.text();
    let data = {};
    if (raw) {
      try {
        data = JSON.parse(raw);
      } catch (_) {
        data = { error: raw };
      }
    }
    if (!response.ok) {
      throw new Error(data.error || `HTTP ${response.status}`);
    }
    return data;
  }

  function setStatus(text, tone = 'muted') {
    if (!els.status) return;
    els.status.textContent = text || '';
    els.status.className = tone === 'danger' ? 'sz_error' : 'sz_text_muted';
  }

  function normalizeMenuRow(row) {
    const normalized = {
      MENUSTAMP: '',
      NOME: '',
      TABELA: '',
      URL: '',
      ICONE: '',
      ORDEM: 0,
      INATIVO: 0,
      LARGURAS_EXATAS: 0,
      LARGURAS_EXATAS_LISTA: 0,
      CAMPO_COUNT: 0,
      EVENTS: {},
      ...(row || {}),
    };
    if (!normalized.EVENTS || typeof normalized.EVENTS !== 'object' || Array.isArray(normalized.EVENTS)) {
      normalized.EVENTS = {};
    }
    if (row && typeof row === 'object') {
      Object.assign(row, normalized);
      return row;
    }
    return normalized;
  }

  function normalizeCampoRow(row) {
    const normalized = {
      CAMPOSSTAMP: '',
      NMCAMPO: '',
      DESCRICAO: '',
      TIPO: 'TEXT',
      ORDEM: 0,
      TAM: 1,
      ORDEM_MOBILE: 0,
      TAM_MOBILE: 1,
      ORDEM_LISTA: 0,
      TAM_LISTA: 1,
      ORDEM_LISTA_MOBILE: 0,
      TAM_LISTA_MOBILE: 1,
      LISTA_MOBILE_BOLD: 0,
      LISTA_MOBILE_ITALIC: 0,
      LISTA_MOBILE_SHOW_LABEL: 1,
      LISTA_MOBILE_LABEL: '',
      RONLY: 0,
      OBRIGATORIO: 0,
      VISIVEL: 1,
      LISTA: 0,
      FILTRO: 0,
      DECIMAIS: 0,
      MINIMO: '',
      MAXIMO: '',
      COMBO: '',
      CONDICAO_VISIVEL: '',
      PROPRIEDADES: {},
      HAS_COMBO: false,
      _SPV_ORIGIN: 'field',
      _SPV_MISSING: 0,
      _SPV_SQL_TYPE: '',
      _SPV_SQL_CHAR_LEN: 0,
      _SPV_ROW: null,
      _SPV_POS: null,
      _SPV_ROW_MOBILE: null,
      _SPV_POS_MOBILE: null,
      _SPV_ROW_LIST: null,
      _SPV_POS_LIST: null,
      _SPV_ROW_LIST_MOBILE: null,
      _SPV_POS_LIST_MOBILE: null,
      ...(row || {}),
    };
    if (row && typeof row === 'object') {
      Object.assign(row, normalized);
      return row;
    }
    return normalized;
  }

  function normalizeVariableRow(row) {
    const normalized = {
      VARIAVELSTAMP: '',
      NOME: '',
      DESCRICAO: '',
      TIPO: 'TEXT',
      VALOR_DEFAULT: '',
      ORDEM: 0,
      PROPRIEDADES: {},
      _SPV_ORIGIN: 'variable',
      ...(row || {}),
    };
    normalized.TIPO = VARIABLE_TYPES.includes(String(normalized.TIPO || '').trim().toUpperCase())
      ? String(normalized.TIPO || '').trim().toUpperCase()
      : 'TEXT';
    if (!normalized.PROPRIEDADES || typeof normalized.PROPRIEDADES !== 'object') {
      normalized.PROPRIEDADES = {};
    }
    if (row && typeof row === 'object') {
      Object.assign(row, normalized);
      return row;
    }
    return normalized;
  }

  function detectFieldType(field) {
    const raw = String(field.TIPO || '').trim().toUpperCase();
    if (raw === 'TEXT' && (field.HAS_COMBO || String(field.COMBO || '').trim())) return 'COMBO';
    if (TYPE_META[raw]) return raw;
    return 'TEXT';
  }

  function fieldLabel(field) {
    return String(field.DESCRICAO || field.NMCAMPO || '').trim() || 'Campo';
  }

  function isCustomObject(field) {
    return String(field?._SPV_ORIGIN || '').trim().toLowerCase() === 'object';
  }

  function getDetailFields() {
    return Array.isArray(state.detail?.fields) ? state.detail.fields : [];
  }

  function isSqlField(field) {
    return String(field?._SPV_ORIGIN || '').trim().toLowerCase() === 'sql' || Number(field?._SPV_MISSING || 0) === 1;
  }

  function getScreenObjects() {
    return Array.isArray(state.customObjects) ? state.customObjects : [];
  }

  function getScreenVariables() {
    return Array.isArray(state.variables) ? state.variables : [];
  }

  function getAllScreenItems() {
    return [...getDetailFields(), ...getScreenObjects()];
  }

  function getLayoutItems() {
    if (isListLayoutMode()) {
      return getDetailFields();
    }
    return [...getDetailFields(), ...getScreenObjects()];
  }

  function normalizeVariableName(value) {
    return String(value ?? '')
      .trim()
      .toUpperCase()
      .replace(/[^A-Z0-9_]+/g, '_')
      .replace(/_+/g, '_')
      .replace(/^_+|_+$/g, '')
      .slice(0, 60);
  }

  function nextVariableStamp() {
    return `SPVVAR-${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`.slice(0, 25);
  }

  function getVariableTypeMeta(type) {
    const key = String(type || '').trim().toUpperCase();
    return VARIABLE_META[key] || VARIABLE_META.TEXT;
  }

  function variableLabel(variable) {
    return String(variable?.DESCRICAO || variable?.NOME || '').trim() || 'Variavel';
  }

  function variableHelpText(variable) {
    return String(variable?.PROPRIEDADES?.help_text || '').trim();
  }

  function getEventGroupLabel(groupId) {
    return EVENT_GROUP_LABELS[String(groupId || '').trim()] || String(groupId || '').trim();
  }

  function getEventCommandLabel(commandOrMeta) {
    const command = typeof commandOrMeta === 'string'
      ? String(commandOrMeta || '').trim().toUpperCase()
      : String(commandOrMeta?.id || commandOrMeta?.command || '').trim().toUpperCase();
    return EVENT_COMMAND_LABELS[command]
      || (typeof commandOrMeta === 'object' ? String(commandOrMeta?.label || '').trim() : command);
  }

  function getEventFieldLabel(field) {
    const key = String(field?.key || '').trim();
    return EVENT_FIELD_LABELS[key] || String(field?.label || key).trim();
  }

  function getFieldProperties(field) {
    return field && typeof field.PROPRIEDADES === 'object' && field.PROPRIEDADES
      ? field.PROPRIEDADES
      : {};
  }

  function getFieldBoundVariableName(field) {
    return normalizeVariableName(getFieldProperties(field).variable_name);
  }

  function getFieldBoundVariable(field) {
    const variableName = getFieldBoundVariableName(field);
    if (!variableName) return null;
    return getScreenVariables().find((row) => normalizeVariableName(row?.NOME) === variableName) || null;
  }

  function getFieldBoundVariableDefault(field) {
    const variable = getFieldBoundVariable(field);
    return variable ? String(variable.VALOR_DEFAULT ?? '').trim() : '';
  }

  function isFieldEnabled(field) {
    const props = getFieldProperties(field);
    if (!Object.prototype.hasOwnProperty.call(props, 'enabled')) return true;
    return isTruthyLike(props.enabled);
  }

  function getFieldClickAction(field) {
    return String(getFieldProperties(field).click_action || '').trim();
  }

  function getFieldEvents(field) {
    const props = getFieldProperties(field);
    return props.events && typeof props.events === 'object' && !Array.isArray(props.events)
      ? props.events
      : {};
  }

  function getScreenMenu() {
    return normalizeMenuRow(state.detail?.menu || {});
  }

  function getMenuEvents(menu = getScreenMenu()) {
    return menu.EVENTS && typeof menu.EVENTS === 'object' && !Array.isArray(menu.EVENTS)
      ? menu.EVENTS
      : {};
  }

  function hasFieldLegacyScript(field, eventName = 'click') {
    if (String(eventName || '').trim().toLowerCase() !== 'click') return false;
    return !!getFieldClickAction(field);
  }

  function nextEventLineId() {
    state.eventLineSeq += 1;
    return `SPVEVT-${Date.now().toString(36)}${state.eventLineSeq.toString(36)}`.slice(0, 25);
  }

  function cloneJson(value, fallback = null) {
    try {
      return JSON.parse(JSON.stringify(value));
    } catch (_) {
      return fallback;
    }
  }

  function createEventLine(line = {}) {
    const kind = String(line?.kind || line?.type || 'command').trim().toLowerCase() === 'empty'
      ? 'empty'
      : 'command';
    const command = kind === 'command'
      ? String(line?.command || line?.id || line?.type || 'START').trim().toUpperCase()
      : '';
    return {
      id: String(line?.id || '').trim() || nextEventLineId(),
      kind,
      command,
      config: line?.config && typeof line.config === 'object' && !Array.isArray(line.config)
        ? (cloneJson(line.config, {}) || {})
        : {},
    };
  }

  function isEventEmptyLine(line) {
    return String(line?.kind || '').trim().toLowerCase() === 'empty';
  }

  function isEventStructuralCommand(command) {
    return ['ELSE', 'ENDIF', 'ENDWHILE', 'ENDFOR', 'ENDCURSOR_SCAN'].includes(String(command || '').trim().toUpperCase());
  }

  function isEventBlockOpenCommand(command) {
    return ['IF', 'WHILE', 'FOR_EACH', 'CURSOR_SCAN'].includes(String(command || '').trim().toUpperCase());
  }

  function isEventBlockCloseCommand(command) {
    return ['ENDIF', 'ENDWHILE', 'ENDFOR', 'ENDCURSOR_SCAN'].includes(String(command || '').trim().toUpperCase());
  }

  function isEventDraggableCommand(command) {
    return !['START', 'IF', 'ELSE', 'ENDIF', 'WHILE', 'ENDWHILE', 'FOR_EACH', 'ENDFOR', 'CURSOR_SCAN', 'ENDCURSOR_SCAN'].includes(
      String(command || '').trim().toUpperCase(),
    );
  }

  function getFieldEventDefinition(field, eventName = 'click') {
    const key = String(eventName || '').trim().toLowerCase();
    return getFieldEvents(field)[key] || null;
  }

  function getMenuEventDefinition(menu = getScreenMenu(), eventName = 'init') {
    const key = String(eventName || '').trim().toLowerCase();
    return getMenuEvents(menu)[key] || null;
  }

  function normalizeEventFlow(rawFlow) {
    const rawLines = Array.isArray(rawFlow?.lines) ? rawFlow.lines : [];
    const normalizedLines = rawLines
      .map(createEventLine)
      .filter((line) => line.kind === 'empty' || EVENT_COMMAND_META[line.command]);
    const collapsed = [];
    normalizedLines.forEach((line) => {
      if (isEventEmptyLine(line) && isEventEmptyLine(collapsed[collapsed.length - 1])) return;
      collapsed.push(line);
    });
    const lines = collapsed.length ? collapsed : [createEventLine({ command: 'START' })];
    return {
      version: 1,
      source: 'visual-editor',
      lines,
      pseudo_code: String(rawFlow?.pseudo_code || '').trim(),
    };
  }

  function countEventCommands(flow, { meaningfulOnly = false } = {}) {
    const lines = Array.isArray(flow?.lines) ? flow.lines : [];
    return lines.filter((line) => {
      if (isEventEmptyLine(line)) return false;
      if (!meaningfulOnly) return true;
      return !['START', 'ELSE', 'ENDIF', 'ENDWHILE', 'ENDFOR', 'ENDCURSOR_SCAN'].includes(String(line.command || '').trim().toUpperCase());
    }).length;
  }

  function hasFieldVisualEvent(field, eventName = 'click') {
    const flow = getFieldEventDefinition(field, eventName);
    if (!flow || !Array.isArray(flow?.lines) || !flow.lines.length) return false;
    return countEventCommands(normalizeEventFlow(flow), { meaningfulOnly: true }) > 0;
  }

  function hasFieldEventConfigured(field, eventName = 'click') {
    return hasFieldVisualEvent(field, eventName) || hasFieldLegacyScript(field, eventName);
  }

  function hasMenuVisualEvent(menu = getScreenMenu(), eventName = 'init') {
    const flow = getMenuEventDefinition(menu, eventName);
    if (!flow || !Array.isArray(flow?.lines) || !flow.lines.length) return false;
    return countEventCommands(normalizeEventFlow(flow), { meaningfulOnly: true }) > 0;
  }

  function hasMenuEventConfigured(menu = getScreenMenu(), eventName = 'init') {
    return hasMenuVisualEvent(menu, eventName);
  }

  function getFieldEventSummary(field, eventName = 'click') {
    const visualFlow = getFieldEventDefinition(field, eventName);
    const visualSteps = visualFlow && Array.isArray(visualFlow?.lines)
      ? countEventCommands(normalizeEventFlow(visualFlow), { meaningfulOnly: true })
      : 0;
    if (visualSteps > 0) {
      return `${visualSteps} passo${visualSteps === 1 ? '' : 's'} visuais`;
    }
    if (hasFieldLegacyScript(field, eventName)) {
      return 'Script JS legado';
    }
    return 'Sem evento configurado';
  }

  function getMenuEventSummary(menu = getScreenMenu(), eventName = 'init') {
    const visualFlow = getMenuEventDefinition(menu, eventName);
    const visualSteps = visualFlow && Array.isArray(visualFlow?.lines)
      ? countEventCommands(normalizeEventFlow(visualFlow), { meaningfulOnly: true })
      : 0;
    if (visualSteps > 0) {
      return `${visualSteps} passo${visualSteps === 1 ? '' : 's'} visuais`;
    }
    return 'Sem evento configurado';
  }

  function getFieldEventPseudoCode(field, eventName = 'click') {
    const rawFlow = getFieldEventDefinition(field, eventName);
    if (!rawFlow || !Array.isArray(rawFlow?.lines) || !rawFlow.lines.length) return '';
    return buildEventPseudoCode(normalizeEventFlow(rawFlow));
  }

  function isTruthyLike(value) {
    if (typeof value === 'boolean') return value;
    const raw = String(value ?? '').trim().toLowerCase();
    return ['1', 'true', 'yes', 'sim', 'on'].includes(raw);
  }

  function sortVariablesForList(rows) {
    return (Array.isArray(rows) ? rows.slice() : [])
      .map(normalizeVariableRow)
      .sort((a, b) => {
        const orderDiff = Number(a.ORDEM || 0) - Number(b.ORDEM || 0);
        if (orderDiff !== 0) return orderDiff;
        return variableLabel(a).localeCompare(variableLabel(b));
      });
  }

  function prepareVariables(rows) {
    return sortVariablesForList(rows);
  }

  function syncVariableOrder() {
    state.variables = sortVariablesForList(getScreenVariables());
    state.variables.forEach((variable, index) => {
      variable.ORDEM = (index + 1) * 10;
    });
    return state.variables;
  }

  function findVariableByStamp(variableStamp) {
    const stamp = String(variableStamp || '').trim();
    if (!stamp) return null;
    return getScreenVariables().find((row) => String(row.VARIAVELSTAMP || '').trim() === stamp) || null;
  }

  function getDefaultVariableStamp() {
    const first = sortVariablesForList(getScreenVariables())[0];
    return String(first?.VARIAVELSTAMP || '').trim();
  }

  function ensureSelectedVariable() {
    const current = findVariableByStamp(state.selectedVariableStamp);
    if (current) return;
    state.selectedVariableStamp = getDefaultVariableStamp();
  }

  function getFieldOrderValue(field, mode = state.viewportMode) {
    const fallbackMode = getCurrentLayoutMode();
    const normalizedMode = String(mode || fallbackMode).trim().toLowerCase();
    const key = normalizedMode === 'list_mobile'
      ? 'ORDEM_LISTA_MOBILE'
      : normalizedMode === 'list'
      ? 'ORDEM_LISTA'
      : normalizedMode === 'mobile'
      ? 'ORDEM_MOBILE'
      : 'ORDEM';
    return Number(field?.[key] || 0);
  }

  function isVisibleField(field) {
    const layoutMode = getCurrentLayoutMode();
    if (layoutMode === 'list') {
      const rowKey = getActiveRowKey();
      if (field && Number.isFinite(Number(field?.[rowKey])) && Number(field[rowKey]) > 0) {
        return Number(field.LISTA || 0) === 1;
      }
      return Number(field?.LISTA || 0) === 1 && Number(field?.ORDEM_LISTA || 0) > 0;
    }
    if (layoutMode === 'list_mobile') {
      const rowKey = getActiveRowKey();
      if (field && Number.isFinite(Number(field?.[rowKey])) && Number(field[rowKey]) > 0) {
        return true;
      }
      return Number(field?.ORDEM_LISTA_MOBILE || 0) > 0;
    }
    const rowKey = getActiveRowKey();
    if (field && Number.isFinite(Number(field?.[rowKey])) && Number(field[rowKey]) > 0) {
      return true;
    }
    return getFieldOrderValue(field) > 0;
  }

  function getFieldStamp(field) {
    return String(field?.CAMPOSSTAMP || field?.NMCAMPO || '').trim();
  }

  function getFieldRowId(field) {
    const rowKey = getActiveRowKey();
    if (field && Number.isFinite(Number(field?.[rowKey])) && Number(field[rowKey]) >= 0) {
      return Number(field[rowKey]);
    }
    const order = getFieldOrderValue(field);
    if (order <= 0) return -1;
    return Math.floor(order / 10);
  }

  function getFieldPos(field) {
    const posKey = getActivePosKey();
    if (field && Number.isFinite(Number(field?.[posKey])) && Number(field[posKey]) >= 0) {
      return Number(field[posKey]);
    }
    const order = getFieldOrderValue(field);
    return order > 0 ? (order % 10) : 0;
  }

  function compareLayoutFields(a, b) {
    const ar = getFieldRowId(a);
    const br = getFieldRowId(b);
    if (ar !== br) return ar - br;
    const ap = getFieldPos(a);
    const bp = getFieldPos(b);
    if (ap !== bp) return ap - bp;
    return fieldLabel(a).localeCompare(fieldLabel(b));
  }

  function assignInitialLocalPositions(fields, mode = 'desktop') {
    const orderKey = getOrderFieldForMode(mode);
    const rowKey = getRowKeyForMode(mode);
    const posKey = getPosKeyForMode(mode);
    if (String(mode || '').trim().toLowerCase() === 'list') {
      fields
        .filter((field) => Number(field?.[orderKey] || 0) > 0)
        .sort((a, b) => Number(a?.[orderKey] || 0) - Number(b?.[orderKey] || 0))
        .forEach((field, index) => {
          field[rowKey] = 1;
          field[posKey] = index;
        });
      fields
        .filter((field) => Number(field?.[orderKey] || 0) <= 0)
        .forEach((field) => {
          field[rowKey] = -1;
          field[posKey] = 9999;
        });
      return;
    }
    const grouped = new Map();
    fields
      .filter((field) => Number(field?.[orderKey] || 0) > 0)
      .sort((a, b) => Number(a?.[orderKey] || 0) - Number(b?.[orderKey] || 0))
      .forEach((field) => {
        const rowId = Math.floor(Number(field?.[orderKey] || 0) / 10);
        if (!grouped.has(rowId)) grouped.set(rowId, []);
        grouped.get(rowId).push(field);
      });
    grouped.forEach((rowFields, rowId) => {
      rowFields.forEach((field, index) => {
        field[rowKey] = rowId;
        field[posKey] = index;
      });
    });
    fields
      .filter((field) => Number(field?.[orderKey] || 0) <= 0)
      .forEach((field) => {
        field[rowKey] = -1;
        field[posKey] = 9999;
      });
  }

  function prepareLocalFields(rows) {
    const fields = Array.isArray(rows) ? rows.map(normalizeCampoRow) : [];
    assignInitialLocalPositions(fields, 'desktop');
    assignInitialLocalPositions(fields, 'mobile');
    assignInitialLocalPositions(fields, 'list');
    assignInitialLocalPositions(fields, 'list_mobile');
    return fields;
  }

  function defaultListWidth(field) {
    const current = Math.max(0, Number(field?.TAM_LISTA || 0));
    if (current > 0) return current;
    return Math.max(5, Number(field?.TAM || 0) || 10);
  }

  function defaultListMobileWidth(field) {
    const current = Math.max(0, Number(field?.TAM_LISTA_MOBILE || 0));
    if (current > 0) return current;
    if (Number(field?.TAM_MOBILE || 0) > 0) return Math.max(5, Number(field.TAM_MOBILE || 0));
    if (Number(field?.TAM_LISTA || 0) > 0) return Math.max(5, Number(field.TAM_LISTA || 0));
    return Math.max(5, Number(field?.TAM || 0) || 10);
  }

  function normalizeListDesktopLayout() {
    const fields = getDetailFields().map(normalizeCampoRow);
    const visible = fields
      .filter((field) => Number(field.LISTA || 0) === 1)
      .sort((a, b) => {
        const aOrder = Number(a.ORDEM_LISTA || a.ORDEM || 0);
        const bOrder = Number(b.ORDEM_LISTA || b.ORDEM || 0);
        if (aOrder !== bOrder) return aOrder - bOrder;
        return fieldLabel(a).localeCompare(fieldLabel(b));
      });

    const included = new Set();
    visible.forEach((field, index) => {
      included.add(getFieldStamp(field));
      field.LISTA = 1;
      field.TAM_LISTA = defaultListWidth(field);
      field._SPV_ROW_LIST = 1;
      field._SPV_POS_LIST = index;
      field.ORDEM_LISTA = (index + 1) * 10;
    });

    fields.forEach((field) => {
      if (included.has(getFieldStamp(field))) return;
      field.TAM_LISTA = defaultListWidth(field);
      field._SPV_ROW_LIST = -1;
      field._SPV_POS_LIST = 9999;
      field.ORDEM_LISTA = 0;
    });
  }

  function normalizeListMobileLayout() {
    const fields = getDetailFields().map(normalizeCampoRow);
    const visible = fields
      .filter((field) => Number(field.ORDEM_LISTA_MOBILE || 0) > 0)
      .sort((a, b) => {
        const orderDiff = Number(a.ORDEM_LISTA_MOBILE || 0) - Number(b.ORDEM_LISTA_MOBILE || 0);
        if (orderDiff !== 0) return orderDiff;
        return fieldLabel(a).localeCompare(fieldLabel(b));
      });

    visible.forEach((field) => {
      field.TAM_LISTA_MOBILE = defaultListMobileWidth(field);
      if (field.LISTA_MOBILE_SHOW_LABEL === undefined || field.LISTA_MOBILE_SHOW_LABEL === null) {
        field.LISTA_MOBILE_SHOW_LABEL = 1;
      }
      if (!String(field.LISTA_MOBILE_LABEL || '').trim()) {
        field.LISTA_MOBILE_LABEL = String(field.DESCRICAO || field.NMCAMPO || '').trim();
      }
    });

    assignInitialLocalPositions(visible, 'list_mobile');

    fields
      .filter((field) => Number(field.ORDEM_LISTA_MOBILE || 0) <= 0)
      .forEach((field) => {
        field.TAM_LISTA_MOBILE = defaultListMobileWidth(field);
        if (field.LISTA_MOBILE_SHOW_LABEL === undefined || field.LISTA_MOBILE_SHOW_LABEL === null) {
          field.LISTA_MOBILE_SHOW_LABEL = 1;
        }
        if (!String(field.LISTA_MOBILE_LABEL || '').trim()) {
          field.LISTA_MOBILE_LABEL = String(field.DESCRICAO || field.NMCAMPO || '').trim();
        }
        field._SPV_ROW_LIST_MOBILE = -1;
        field._SPV_POS_LIST_MOBILE = 9999;
        field.ORDEM_LISTA_MOBILE = 0;
      });
  }

  function getVisibleListFields({ excludeStamp = '' } = {}) {
    const stamp = String(excludeStamp || '').trim();
    normalizeListDesktopLayout();
    return getDetailFields()
      .map(normalizeCampoRow)
      .filter((field) => {
        if (stamp && getFieldStamp(field) === stamp) return false;
        return Number(field.LISTA || 0) === 1 && Number(field.ORDEM_LISTA || 0) > 0;
      })
      .sort((a, b) => Number(a.ORDEM_LISTA || 0) - Number(b.ORDEM_LISTA || 0));
  }

  function getVisibleListMobileFields({ excludeStamp = '' } = {}) {
    const stamp = String(excludeStamp || '').trim();
    normalizeListMobileLayout();
    return getDetailFields()
      .map(normalizeCampoRow)
      .filter((field) => {
        if (stamp && getFieldStamp(field) === stamp) return false;
        return Number(field.ORDEM_LISTA_MOBILE || 0) > 0;
      })
      .sort((a, b) => Number(a.ORDEM_LISTA_MOBILE || 0) - Number(b.ORDEM_LISTA_MOBILE || 0));
  }

  function applyListFieldSequence(nextFields) {
    const sequence = Array.isArray(nextFields) ? nextFields.map(normalizeCampoRow) : [];
    const included = new Set(sequence.map((field) => getFieldStamp(field)).filter(Boolean));
    sequence.forEach((field, index) => {
      field.LISTA = 1;
      field.TAM_LISTA = defaultListWidth(field);
      field._SPV_ROW_LIST = 1;
      field._SPV_POS_LIST = index;
      field.ORDEM_LISTA = (index + 1) * 10;
    });
    getDetailFields().map(normalizeCampoRow).forEach((field) => {
      if (included.has(getFieldStamp(field))) return;
      field.LISTA = 0;
      field.TAM_LISTA = defaultListWidth(field);
      field._SPV_ROW_LIST = -1;
      field._SPV_POS_LIST = 9999;
      field.ORDEM_LISTA = 0;
    });
  }

  function toggleFieldInListMobile(fieldStamp, shouldShow) {
    const target = findFieldByStamp(fieldStamp);
    if (!target) return false;
    if (!shouldShow) {
      target._SPV_ROW_LIST_MOBILE = -1;
      target._SPV_POS_LIST_MOBILE = 9999;
      target.ORDEM_LISTA_MOBILE = 0;
      target.TAM_LISTA_MOBILE = defaultListMobileWidth(target);
      return true;
    }

    const visible = getVisibleListMobileFields({ excludeStamp: fieldStamp });
    const grouped = new Map();
    visible.forEach((field) => {
      const rowId = Math.max(1, Number(field._SPV_ROW_LIST_MOBILE || Math.floor(Number(field.ORDEM_LISTA_MOBILE || 0) / 10) || 1));
      if (!grouped.has(rowId)) grouped.set(rowId, []);
      grouped.get(rowId).push(field);
    });
    const nextRowId = grouped.size ? Math.max(...grouped.keys()) + 1 : 1;
    target._SPV_ROW_LIST_MOBILE = nextRowId;
    target._SPV_POS_LIST_MOBILE = 0;
    target.TAM_LISTA_MOBILE = defaultListMobileWidth(target);
    normalizeLocalLayout(getDetailFields());
    return true;
  }

  function moveFieldToList(fieldStamp, index) {
    const target = findFieldByStamp(fieldStamp);
    if (!target) return false;
    const nextFields = getVisibleListFields({ excludeStamp: fieldStamp });
    const nextIndex = Math.max(0, Math.min(Number(index) || 0, nextFields.length));
    nextFields.splice(nextIndex, 0, target);
    applyListFieldSequence(nextFields);
    return true;
  }

  function hydrateLoadedDetail(detail) {
    const fields = prepareLocalFields(detail?.fields);
    const objects = prepareLocalFields(detail?.objects || []);
    const variables = prepareVariables(detail?.variables || []);
    const combined = [...fields, ...objects];

    // ORDEM usa a dezena como linha e a unidade como posição na linha.
    // A hidratação tem de ser feita sobre o layout completo, não separando campos e objetos.
    assignInitialLocalPositions(combined, 'desktop');
    assignInitialLocalPositions(combined, 'mobile');
    fields
      .filter((field) => Number(field.LISTA || 0) === 1 && Number(field.ORDEM_LISTA || 0) <= 0)
      .forEach((field) => {
        field.ORDEM_LISTA = Number(field.ORDEM || 0);
      });
    normalizeListMobileLayout();

    return {
      menu: normalizeMenuRow(detail?.menu || {}),
      fields,
      objects,
      variables,
    };
  }

  function getVisibleLayoutFields(fields = getLayoutItems()) {
    return (Array.isArray(fields) ? fields : [])
      .map(normalizeCampoRow)
      .filter((field) => isVisibleField(field))
      .sort(compareLayoutFields);
  }

  function syncLocalOrder(fields = getLayoutItems()) {
    const orderKey = getActiveOrderField();
    (Array.isArray(fields) ? fields : [])
      .map(normalizeCampoRow)
      .forEach((field) => {
        if (!isVisibleField(field) || getFieldRowId(field) < 0) {
          field[orderKey] = 0;
          return;
        }
        if (getCurrentLayoutMode() === 'list') {
          field[orderKey] = (getFieldPos(field) + 1) * 10;
          return;
        }
        field[orderKey] = (getFieldRowId(field) * 10) + getFieldPos(field) + 1;
      });
  }

  function normalizeLocalLayout(fields = getLayoutItems()) {
    const rowKey = getActiveRowKey();
    const posKey = getActivePosKey();
    const visible = getVisibleLayoutFields(fields);
    const rowMap = new Map();
    let nextRowId = 1;
    visible.forEach((field) => {
      const rowId = getFieldRowId(field);
      if (!rowMap.has(rowId)) rowMap.set(rowId, nextRowId++);
      field[rowKey] = rowMap.get(rowId);
    });
    const rowCounters = new Map();
    visible.forEach((field) => {
      const rowId = getFieldRowId(field);
      const index = rowCounters.get(rowId) || 0;
      field[posKey] = index;
      rowCounters.set(rowId, index + 1);
    });
    (Array.isArray(fields) ? fields : [])
      .map(normalizeCampoRow)
      .filter((field) => !isVisibleField(field))
      .forEach((field) => {
        field[rowKey] = -1;
        field[posKey] = 9999;
      });
    syncLocalOrder(fields);
    return fields;
  }

  function getRowFields(rowId, { excludeStamp = '' } = {}) {
    const stamp = String(excludeStamp || '').trim();
    return getVisibleLayoutFields().filter((field) => {
      if (stamp && getFieldStamp(field) === stamp) return false;
      return getFieldRowId(field) === Number(rowId);
    });
  }

  function getRowGroups({ excludeStamp = '' } = {}) {
    const stamp = String(excludeStamp || '').trim();
    return groupPreviewFields(getLayoutItems()).map(([rowId, rowFields]) => ({
      rowId: Number(rowId),
      fields: rowFields.filter((field) => !stamp || getFieldStamp(field) !== stamp),
    }));
  }

  function applyRowGroups(groups) {
    const normalizedGroups = Array.isArray(groups) ? groups : [];
    const included = new Set();

    normalizedGroups.forEach((group, rowIndex) => {
      const rowId = rowIndex + 1;
      const rowFields = Array.isArray(group?.fields) ? group.fields : [];
      rowFields.forEach((field, pos) => {
        const item = normalizeCampoRow(field);
        item[getActiveRowKey()] = rowId;
        item[getActivePosKey()] = pos;
        included.add(getFieldStamp(item));
      });
    });

    getLayoutItems().map(normalizeCampoRow).forEach((field) => {
      const stamp = getFieldStamp(field);
      if (included.has(stamp)) return;
      field[getActiveRowKey()] = -1;
      field[getActivePosKey()] = 9999;
      field[getActiveOrderField()] = 0;
    });

    syncLocalOrder();
    normalizeLocalLayout();
  }

  function getFieldSize(field) {
    return Math.min(getPreviewGridUnits(), Math.max(5, Number(field?.[getActiveWidthField()] || 5)));
  }

  function getRowUsedWidth(rowId, { excludeStamp = '' } = {}) {
    return getRowFields(rowId, { excludeStamp }).reduce((acc, field) => acc + getFieldSize(field), 0);
  }

  function getDragSize(drag) {
    if (!drag) return 0;
    if (String(drag.sourceKind || 'layout') === 'catalog') return 5;
    const target = findFieldByStamp(drag.fieldStamp);
    return target ? getFieldSize(target) : 0;
  }

  function canFieldFitRow(fieldStamp, rowId, { sourceKind = 'layout' } = {}) {
    const used = getRowUsedWidth(rowId, {
      excludeStamp: sourceKind === 'layout' ? fieldStamp : '',
    });
    const size = sourceKind === 'catalog'
      ? 5
      : getFieldSize(findFieldByStamp(fieldStamp));
    return size > 0 && (used + size) <= getPreviewGridUnits();
  }

  function moveFieldToRow(fieldStamp, rowId, index) {
    const target = findFieldByStamp(fieldStamp);
    if (!target) return false;
    const sourceRowId = getFieldRowId(target);
    const targetRowId = Number(rowId);
    const sourceStamp = getFieldStamp(target);
    const targetFields = getRowFields(targetRowId, { excludeStamp: sourceStamp });
    const nextIndex = Math.max(0, Math.min(Number(index) || 0, targetFields.length));
    if (sourceRowId === targetRowId) {
      targetFields.splice(nextIndex, 0, target);
      targetFields.forEach((field, pos) => {
        field[getActiveRowKey()] = targetRowId;
        field[getActivePosKey()] = pos;
      });
      normalizeLocalLayout();
      return true;
    }

    const sourceFields = getRowFields(sourceRowId, { excludeStamp: sourceStamp });
    sourceFields.forEach((field, pos) => {
      field[getActiveRowKey()] = sourceRowId;
      field[getActivePosKey()] = pos;
    });
    targetFields.splice(nextIndex, 0, target);
    targetFields.forEach((field, pos) => {
      field[getActiveRowKey()] = targetRowId;
      field[getActivePosKey()] = pos;
    });
    normalizeLocalLayout();
    return true;
  }

  function insertFieldAsNewRow(fieldStamp, beforeRowId, { sourceKind = 'layout', templateId = '' } = {}) {
    const groups = getRowGroups({
      excludeStamp: sourceKind === 'layout' ? fieldStamp : '',
    });
    const target = sourceKind === 'catalog'
      ? createCustomObjectFromTemplate(templateId)
      : findFieldByStamp(fieldStamp);
    if (!target) return null;

    let insertAt = groups.length;
    const before = Number(beforeRowId || 0);
    if (before > 0) {
      const foundIndex = groups.findIndex((group) => Number(group.rowId || 0) === before);
      insertAt = foundIndex >= 0 ? foundIndex : groups.length;
    }

    groups.splice(insertAt, 0, {
      rowId: before > 0 ? before : (groups.length + 1),
      fields: [target],
    });
    applyRowGroups(groups);
    return target;
  }

  function createCustomObjectFromTemplate(templateId) {
    const template = OBJECT_LIBRARY.find((item) => item.id === templateId);
    if (!template) return null;
    const stamp = nextCustomObjectStamp();
    const baseName = `OBJ_${template.id}_${state.customObjectSeq}`;
    const defaultWidth = template.id === 'TABLE' ? 100 : (template.id === 'BUTTON' ? 15 : 5);
    const defaultMobileWidth = template.id === 'TABLE' ? 40 : defaultWidth;
    const objectRow = normalizeCampoRow({
      CAMPOSSTAMP: stamp,
      NMCAMPO: baseName,
      DESCRICAO: template.label,
      TIPO: template.id,
      TAM: defaultWidth,
      TAM_MOBILE: defaultMobileWidth,
      ORDEM: 0,
      ORDEM_MOBILE: 0,
      RONLY: 0,
      OBRIGATORIO: 0,
      LISTA: 0,
      FILTRO: 0,
      DECIMAIS: template.id === 'DECIMAL' ? 2 : 0,
      MINIMO: '',
      MAXIMO: '',
      CONDICAO_VISIVEL: '',
      PROPRIEDADES: {},
      _SPV_ORIGIN: 'object',
      _SPV_ROW: -1,
      _SPV_POS: 9999,
    });
    state.customObjects.push(objectRow);
    return objectRow;
  }

  function insertCustomObjectToRow(templateId, rowId, index) {
    const created = createCustomObjectFromTemplate(templateId);
    if (!created) return null;
    const targetRowId = Number(rowId);
    const targetFields = getRowFields(targetRowId);
    const nextIndex = Math.max(0, Math.min(Number(index) || 0, targetFields.length));
    targetFields.splice(nextIndex, 0, created);
    targetFields.forEach((field, pos) => {
      field[getActiveRowKey()] = targetRowId;
      field[getActivePosKey()] = pos;
    });
    normalizeLocalLayout();
    return created;
  }

  function getDefaultFieldStamp() {
    const visible = getLayoutItems()
      .map(normalizeCampoRow)
      .filter((field) => isVisibleField(field))
      .sort(compareLayoutFields);
    return getFieldStamp(visible[0] || {});
  }

  function ensureSelectedField() {
    const current = findKnownFieldByStamp(state.selectedFieldStamp);
    if (current) return;
    state.selectedFieldStamp = getDefaultFieldStamp();
  }

  function getDefaultSelectionScope() {
    return getDefaultFieldStamp() ? 'field' : 'screen';
  }

  function selectScreen({ render = true } = {}) {
    state.selectedScope = 'screen';
    if (render) renderAll();
  }

  function syncWidthModeFromMenu(menuRow) {
    const menu = normalizeMenuRow(menuRow || {});
    state.useExactWidths = isListLayoutMode()
      ? Number(menu.LARGURAS_EXATAS_LISTA || 0) === 1
      : Number(menu.LARGURAS_EXATAS || 0) === 1;
  }

  function renderActionState() {
    const hasScreen = !!String(state.detail?.menu?.MENUSTAMP || '').trim();
    if (els.saveBtn) els.saveBtn.disabled = !hasScreen || state.loading || state.saving;
    if (els.cancelBtn) els.cancelBtn.disabled = !hasScreen || state.loading || state.saving;
  }

  function buildSavePayload() {
    const menu = normalizeMenuRow(state.detail?.menu || {});
    syncVariableOrder();
    const serializeItem = (row) => {
      const field = normalizeCampoRow(row);
      return {
        CAMPOSSTAMP: getFieldStamp(field),
        NMCAMPO: String(field.NMCAMPO || '').trim(),
        DESCRICAO: String(field.DESCRICAO || '').trim(),
        TIPO: String(field.TIPO || '').trim(),
        ORDEM: Number(field.ORDEM || 0),
        TAM: Number(field.TAM || 0),
        ORDEM_MOBILE: Number(field.ORDEM_MOBILE || 0),
        TAM_MOBILE: Number(field.TAM_MOBILE || 0),
        ORDEM_LISTA: Number(field.ORDEM_LISTA || 0),
        TAM_LISTA: Number(field.TAM_LISTA || 0),
        ORDEM_LISTA_MOBILE: Number(field.ORDEM_LISTA_MOBILE || 0),
        TAM_LISTA_MOBILE: Number(field.TAM_LISTA_MOBILE || 0),
        LISTA_MOBILE_BOLD: Number(field.LISTA_MOBILE_BOLD || 0) ? 1 : 0,
        LISTA_MOBILE_ITALIC: Number(field.LISTA_MOBILE_ITALIC || 0) ? 1 : 0,
        LISTA_MOBILE_SHOW_LABEL: Number(field.LISTA_MOBILE_SHOW_LABEL ?? 1) ? 1 : 0,
        LISTA_MOBILE_LABEL: String(field.LISTA_MOBILE_LABEL || '').trim(),
        RONLY: Number(field.RONLY || 0),
        OBRIGATORIO: Number(field.OBRIGATORIO || 0),
        VISIVEL: Number(field.VISIVEL ?? 1) ? 1 : 0,
        LISTA: Number(field.LISTA || 0),
        FILTRO: Number(field.FILTRO || 0),
        DECIMAIS: Number(field.DECIMAIS || 0),
        MINIMO: String(field.MINIMO ?? '').trim(),
        MAXIMO: String(field.MAXIMO ?? '').trim(),
        COMBO: String(field.COMBO || '').trim(),
        CONDICAO_VISIVEL: String(field.CONDICAO_VISIVEL || '').trim(),
        PROPRIEDADES: field.PROPRIEDADES && typeof field.PROPRIEDADES === 'object'
          ? field.PROPRIEDADES
          : {},
        _SPV_ORIGIN: String(field._SPV_ORIGIN || 'field').trim(),
      };
    };
    const serializeVariable = (row) => {
      const variable = normalizeVariableRow(row);
      return {
        VARIAVELSTAMP: String(variable.VARIAVELSTAMP || '').trim(),
        NOME: normalizeVariableName(variable.NOME),
        DESCRICAO: String(variable.DESCRICAO || '').trim(),
        TIPO: String(variable.TIPO || 'TEXT').trim().toUpperCase(),
        VALOR_DEFAULT: String(variable.VALOR_DEFAULT ?? '').trim(),
        ORDEM: Number(variable.ORDEM || 0),
        PROPRIEDADES: variable.PROPRIEDADES && typeof variable.PROPRIEDADES === 'object'
          ? variable.PROPRIEDADES
          : {},
      };
    };
    return {
      menustamp: String(menu.MENUSTAMP || '').trim(),
      use_exact_widths: Number(menu.LARGURAS_EXATAS || 0) ? 1 : 0,
      use_exact_widths_list: Number(menu.LARGURAS_EXATAS_LISTA || 0),
      screen_events: cloneJson(getMenuEvents(menu), {}) || {},
      fields: getDetailFields().map(serializeItem),
      objects: getScreenObjects().map(serializeItem),
      variables: getScreenVariables().map(serializeVariable),
    };
  }

  async function saveLayout() {
    const menustamp = String(state.detail?.menu?.MENUSTAMP || '').trim();
    if (!menustamp) {
      setStatus('Seleciona um ecr? para gravar.', 'danger');
      return;
    }

    state.saving = true;
    renderActionState();
    setStatus('A gravar layout...');

    try {
      const payload = buildSavePayload();
      const response = await fetchJson(cfg.saveUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const detail = response?.detail || null;
      if (detail) {
        const hydrated = hydrateLoadedDetail(detail);
        state.detail = {
          menu: hydrated.menu,
          fields: hydrated.fields,
        };
        state.customObjects = hydrated.objects;
        state.variables = hydrated.variables;
        state.customObjectSeq = 0;
        state.selectedVariableStamp = getDefaultVariableStamp();
        normalizeListDesktopLayout();
        normalizeListMobileLayout();
      } else {
        state.detail = null;
        state.customObjects = [];
        state.variables = [];
        state.customObjectSeq = 0;
        state.selectedVariableStamp = '';
      }
      if (state.detail?.menu) {
        syncWidthModeFromMenu(state.detail.menu);
      }
      state.selectedFieldStamp = getDefaultFieldStamp();
      state.selectedScope = getDefaultSelectionScope();
      renderAll();
      setStatus('Layout gravado.');
      showToast('Layout gravado.', 'success');
    } catch (error) {
      setStatus(error.message || 'Erro ao gravar o layout.', 'danger');
      showToast(error.message || 'Erro ao gravar o layout.', 'error');
    } finally {
      state.saving = false;
      renderActionState();
    }
  }

  function renderScreenOptions() {
    if (!els.screenSelect) return;
    if (!state.screens.length) {
      els.screenSelect.innerHTML = '<option value="">Sem ecrãs disponíveis</option>';
      els.screenSelect.disabled = true;
      return;
    }

    els.screenSelect.disabled = false;
    els.screenSelect.innerHTML = state.screens.map((row) => {
      const item = normalizeMenuRow(row);
      const extra = [];
      if (item.TABELA) extra.push(item.TABELA);
      if (Number(item.INATIVO || 0)) extra.push('inativo');
      return `<option value="${escapeHtml(item.MENUSTAMP)}">${escapeHtml(item.NOME || item.TABELA || 'Ecrã')} ${extra.length ? `· ${escapeHtml(extra.join(' · '))}` : ''}</option>`;
    }).join('');

    const hasSelected = state.screens.some((row) => String(row.MENUSTAMP || '').trim() === state.selectedMenustamp);
    els.screenSelect.value = hasSelected ? state.selectedMenustamp : String(state.screens[0].MENUSTAMP || '').trim();
    state.selectedMenustamp = String(els.screenSelect.value || '').trim();
  }

  function fieldRowGroup(field) {
    const rowId = getFieldRowId(field);
    if (rowId < 0) return 0;
    return rowId;
  }

  function renderSidebarChrome() {
    const listMode = isListLayoutMode();
    const isFields = state.sidebarMode === 'fields';
    const isObjects = state.sidebarMode === 'objects';
    const isVariables = state.sidebarMode === 'variables';
    const isAdd = state.sidebarMode === 'add';
    if (els.sidebarTitle) {
      els.sidebarTitle.textContent = listMode
        ? 'Campos da Lista'
        : (isFields ? 'Campos' : (isObjects ? 'Objetos' : (isVariables ? 'Variaveis' : 'Adicionar')));
    }
    if (els.layout) {
      els.layout.classList.toggle('is-sidebar-collapsed', !!state.sidebarCollapsed);
    }
    if (els.sidebarFieldsBtn) {
      els.sidebarFieldsBtn.className = isFields ? 'sz_button sz_button_secondary' : 'sz_button sz_button_ghost';
      els.sidebarFieldsBtn.setAttribute('aria-pressed', isFields ? 'true' : 'false');
    }
    if (els.sidebarObjectsBtn) {
      els.sidebarObjectsBtn.className = `${isObjects ? 'sz_button sz_button_secondary' : 'sz_button sz_button_ghost'}${listMode ? ' sz_hidden' : ''}`;
      els.sidebarObjectsBtn.setAttribute('aria-pressed', isObjects ? 'true' : 'false');
    }
    if (els.sidebarVariablesBtn) {
      els.sidebarVariablesBtn.className = `${isVariables ? 'sz_button sz_button_secondary' : 'sz_button sz_button_ghost'}${listMode ? ' sz_hidden' : ''}`;
      els.sidebarVariablesBtn.setAttribute('aria-pressed', isVariables ? 'true' : 'false');
    }
    if (els.sidebarAddBtn) {
      els.sidebarAddBtn.className = `${isAdd ? 'sz_button sz_button_secondary' : 'sz_button sz_button_ghost'}${listMode ? ' sz_hidden' : ''}`;
      els.sidebarAddBtn.setAttribute('aria-pressed', isAdd ? 'true' : 'false');
    }
    if (els.sidebarCollapseBtn) {
      els.sidebarCollapseBtn.title = state.sidebarCollapsed ? 'Expandir painel' : 'Encolher painel';
      els.sidebarCollapseBtn.innerHTML = state.sidebarCollapsed
        ? '<i class="fa-solid fa-angles-right"></i>'
        : '<i class="fa-solid fa-angles-left"></i>';
    }
  }

  function renderObjectList() {
    if (!els.fieldsList) return;
    const objects = getScreenObjects().map(normalizeCampoRow).sort(compareLayoutFields);
    if (!objects.length) {
      els.fieldsList.innerHTML = '<div class="sz_text_muted">Ainda n?o existem objetos adicionais neste ecr?.</div>';
      return;
    }
    els.fieldsList.innerHTML = objects.map((row) => {
      const field = normalizeCampoRow(row);
      const type = detectFieldType(field);
      const meta = TYPE_META[type] || TYPE_META.TEXT;
      const fieldStamp = getFieldStamp(field);
      return `
        <article class="spv-field-card spv-object-card ${state.selectedScope === 'field' && fieldStamp && fieldStamp === state.selectedFieldStamp ? 'is-selected' : ''}" data-campostamp="${escapeHtml(fieldStamp)}">
          <div class="spv-field-icon"><i class="${escapeHtml(meta.icon)}"></i></div>
          <div class="spv-field-card-main">
            <div class="spv-field-name">${escapeHtml(fieldLabel(field))}</div>
            <div class="spv-field-key">${escapeHtml(field.NMCAMPO || type)}</div>
          </div>
        </article>
      `;
    }).join('');
  }

  function shortenCardValue(value) {
    const raw = String(value ?? '').trim();
    if (!raw) return '';
    return raw.length > 42 ? `${raw.slice(0, 39)}...` : raw;
  }

  function renderVariablesList() {
    if (!els.fieldsList) return;
    ensureSelectedVariable();
    const variables = sortVariablesForList(getScreenVariables());
    if (!variables.length) {
      els.fieldsList.innerHTML = '<div class="sz_text_muted">Ainda nao existem variaveis neste ecra.</div>';
      return;
    }
    els.fieldsList.innerHTML = variables.map((row) => {
      const variable = normalizeVariableRow(row);
      const meta = getVariableTypeMeta(variable.TIPO);
      const variableStamp = String(variable.VARIAVELSTAMP || '').trim();
      const defaultValue = shortenCardValue(variable.VALOR_DEFAULT);
      return `
        <article class="spv-field-card spv-variable-card ${state.selectedScope === 'variable' && variableStamp && variableStamp === state.selectedVariableStamp ? 'is-selected' : ''}" data-variable-stamp="${escapeHtml(variableStamp)}">
          <div class="spv-field-icon"><i class="${escapeHtml(meta.icon)}"></i></div>
          <div class="spv-field-card-main">
            <div class="spv-field-name">${escapeHtml(variableLabel(variable))}</div>
            <div class="spv-field-key">${escapeHtml(variable.NOME || meta.label)}</div>
            <div class="spv-card-subline">
              <span class="spv-card-pill">${escapeHtml(meta.label)}</span>
              ${defaultValue ? `<span class="spv-card-pill">Default: ${escapeHtml(defaultValue)}</span>` : ''}
            </div>
          </div>
        </article>
      `;
    }).join('');
  }

  function renderAddObjectCatalog() {
    if (!els.fieldsList) return;
    const objectCards = OBJECT_LIBRARY.map((item) => `
      <article class="spv-field-card spv-object-card is-catalog" data-object-template="${escapeHtml(item.id)}">
        <div class="spv-field-icon"><i class="${escapeHtml(item.icon)}"></i></div>
        <div class="spv-field-card-main">
          <div class="spv-field-name">${escapeHtml(item.label)}</div>
          <div class="spv-field-key">${escapeHtml(item.key)}</div>
        </div>
      </article>
    `).join('');
    const variableCard = `
      <article class="spv-field-card spv-variable-card is-catalog" data-variable-action="create">
        <div class="spv-field-icon"><i class="fa-solid fa-code"></i></div>
        <div class="spv-field-card-main">
          <div class="spv-field-name">Variable</div>
          <div class="spv-field-key">Cria uma variavel associada a este menu</div>
          <div class="spv-card-subline">
            <span class="spv-card-pill">Configurar</span>
          </div>
        </div>
      </article>
    `;
    els.fieldsList.innerHTML = `${variableCard}${objectCards}`;
  }

  function renderFieldsList() {
    if (!els.fieldsList) return;
    const fields = getDetailFields().map(normalizeCampoRow);
    if (isListLayoutMode()) {
      if (isListMobileLayoutMode()) {
        normalizeListMobileLayout();
      } else {
        normalizeListDesktopLayout();
      }
    }
    const sortedFields = fields.slice().sort((a, b) => {
      const am = isSqlField(a);
      const bm = isSqlField(b);
      if (am !== bm) return am ? 1 : -1;
      const av = isVisibleField(a);
      const bv = isVisibleField(b);
      if (av !== bv) return av ? -1 : 1;
      if (isListLayoutMode()) {
        const orderDiff = Number(a[getActiveOrderField()] || 0) - Number(b[getActiveOrderField()] || 0);
        if (orderDiff !== 0) return orderDiff;
      }
      return compareLayoutFields(a, b);
    });

    if (!fields.length) {
      els.fieldsList.innerHTML = '<div class="sz_text_muted">Sem CAMPOS configurados.</div>';
      return;
    }

    els.fieldsList.innerHTML = sortedFields.map((row) => {
      const field = normalizeCampoRow(row);
      const type = detectFieldType(field);
      const meta = TYPE_META[type] || TYPE_META.TEXT;
      const isHidden = !isVisibleField(field);
      const fieldStamp = getFieldStamp(field);
      const sqlField = isSqlField(field);
      return `
        <article class="spv-field-card ${isHidden ? 'is-hidden' : ''} ${sqlField ? 'is-sql' : ''} ${state.selectedScope === 'field' && fieldStamp && fieldStamp === state.selectedFieldStamp ? 'is-selected' : ''}" data-campostamp="${escapeHtml(fieldStamp)}" title="${escapeHtml(sqlField ? 'SQL column not configured in CAMPOS' : (field.NMCAMPO || 'Campo'))}">
          <div class="spv-field-icon"><i class="${escapeHtml(meta.icon)}"></i></div>
          <div class="spv-field-card-main">
            <div class="spv-field-name">${escapeHtml(fieldLabel(field))}</div>
            <div class="spv-field-key">${escapeHtml(field.NMCAMPO)}</div>
          </div>
        </article>
      `;
    }).join('');
  }

  function renderSidebarList() {
    renderSidebarChrome();
    if (isListLayoutMode()) {
      renderFieldsList();
      return;
    }
    if (state.sidebarMode === 'objects') {
      renderObjectList();
      return;
    }
    if (state.sidebarMode === 'variables') {
      renderVariablesList();
      return;
    }
    if (state.sidebarMode === 'add') {
      renderAddObjectCatalog();
      return;
    }
    renderFieldsList();
  }

  function buildResizeHandle(field) {
    return `
      <button
        type="button"
        class="spv-resize-handle"
        data-campostamp="${escapeHtml(field.CAMPOSSTAMP || field.NMCAMPO || '')}"
        title="Arrastar para ajustar a largura"
        aria-label="Ajustar largura"
      ></button>
    `;
  }

  function renderWidthModeToggle() {
    if (!els.exactWidthsBtn || !els.proportionalWidthsBtn) return;
    const exactActive = !!state.useExactWidths;
    els.exactWidthsBtn.className = exactActive ? 'sz_button sz_button_secondary' : 'sz_button sz_button_ghost';
    els.proportionalWidthsBtn.className = exactActive ? 'sz_button sz_button_ghost' : 'sz_button sz_button_secondary';
    els.exactWidthsBtn.setAttribute('aria-pressed', exactActive ? 'true' : 'false');
    els.proportionalWidthsBtn.setAttribute('aria-pressed', exactActive ? 'false' : 'true');
  }

  function renderLayoutModeToggle() {
    if (!els.formModeBtn || !els.listModeBtn) return;
    const listMode = isListLayoutMode();
    els.formModeBtn.className = listMode ? 'sz_button sz_button_ghost' : 'sz_button sz_button_secondary';
    els.listModeBtn.className = listMode ? 'sz_button sz_button_secondary' : 'sz_button sz_button_ghost';
    els.formModeBtn.setAttribute('aria-pressed', listMode ? 'false' : 'true');
    els.listModeBtn.setAttribute('aria-pressed', listMode ? 'true' : 'false');
    if (els.pageSubtitle) {
      els.pageSubtitle.textContent = listMode
        ? 'Configuração visual das colunas desktop e dos cards mobile usados no dynamic_list.'
        : 'Visualização da disposição dos CAMPOS usados no dynamic_form.';
    }
  }

  function renderViewportModeToggle() {
    if (!els.desktopModeBtn || !els.mobileModeBtn) return;
    const mobile = isMobileMode();
    els.desktopModeBtn.className = mobile ? 'sz_button sz_button_ghost' : 'sz_button sz_button_secondary';
    els.mobileModeBtn.className = mobile ? 'sz_button sz_button_secondary' : 'sz_button sz_button_ghost';
    els.desktopModeBtn.setAttribute('aria-pressed', mobile ? 'false' : 'true');
    els.mobileModeBtn.setAttribute('aria-pressed', mobile ? 'true' : 'false');
  }

  function buildPreviewControl(field) {
    const type = detectFieldType(field);
    const boundVariable = getFieldBoundVariable(field);
    const boundValue = getFieldBoundVariableDefault(field);
    const isButton = type === 'BUTTON';
    const isTable = type === 'TABLE';
    const enabled = isFieldEnabled(field);
    const label = `${escapeHtml(fieldLabel(field))}${!isButton && !isTable && Number(field.OBRIGATORIO || 0) ? ' <span class="spv-required">*</span>' : ''}${boundVariable ? ` <span class="sz_badge sz_badge_warning spv-readonly-badge">${escapeHtml(boundVariable.NOME || 'VAR')}</span>` : ''}${!isButton && !isTable && Number(field.RONLY || 0) ? ' <span class="sz_badge sz_badge_warning spv-readonly-badge">R/O</span>' : ''}${isButton && hasFieldEventConfigured(field, 'click') ? ' <span class="sz_badge sz_badge_warning spv-readonly-badge">Click</span>' : ''}`;
    const placeholder = escapeHtml(boundValue || field.NMCAMPO || fieldLabel(field));
    const handle = buildResizeHandle(field);

    if (type === 'BIT') {
      return `
        <label class="sz_checkbox spv-preview-checkbox">
          <input type="checkbox" disabled ${isTruthyLike(boundValue) || Number(field.OBRIGATORIO || 0) ? 'checked' : ''}>
          <span>${escapeHtml(fieldLabel(field))}</span>
        </label>
        ${handle}
      `;
    }

    if (type === 'SPACE') {
      return `
        <div class="spv-preview-spacer" aria-hidden="true"></div>
        ${handle}
      `;
    }

    if (type === 'BUTTON') {
      return `
        <button type="button" class="sz_button sz_button_secondary spv-preview-button" ${enabled ? '' : 'disabled'}>${escapeHtml(fieldLabel(field))}</button>
        ${handle}
      `;
    }

    if (type === 'TABLE') {
      const props = getFieldProperties(field);
      const showAddButton = isTruthyLike(props.show_add_button);
      const showDeleteButton = isTruthyLike(props.show_delete_button);
      return `
        <div class="spv-preview-table-block" aria-hidden="true">
          <div class="spv-preview-table-title">${escapeHtml(String(field.NMCAMPO || fieldLabel(field) || 'TABLE').trim() || 'TABLE')}</div>
          ${showAddButton ? `
            <div class="spv-preview-table-toolbar">
              <button type="button" class="sz_button sz_button_secondary spv-preview-table-action" disabled>
                <i class="fa-solid fa-plus"></i>
                <span>Add line</span>
              </button>
            </div>
          ` : ''}
        <div class="spv-preview-table">
          <div class="spv-preview-table-head">
            <span>ID</span>
            <span>Descricao</span>
            <span>Valor</span>
            ${showDeleteButton ? '<span></span>' : ''}
          </div>
          <div class="spv-preview-table-row">
            <span>1</span>
            <span>${escapeHtml(fieldLabel(field))}</span>
            <span>123,45</span>
            ${showDeleteButton ? '<button type="button" class="spv-preview-table-delete" disabled><i class="fa-solid fa-trash"></i></button>' : ''}
          </div>
          <div class="spv-preview-table-row">
            <span>2</span>
            <span>Registo exemplo</span>
            <span>67,89</span>
            ${showDeleteButton ? '<button type="button" class="spv-preview-table-delete" disabled><i class="fa-solid fa-trash"></i></button>' : ''}
          </div>
          <div class="spv-preview-table-row">
            <span>3</span>
            <span>Mais uma linha</span>
            <span>10,00</span>
            ${showDeleteButton ? '<button type="button" class="spv-preview-table-delete" disabled><i class="fa-solid fa-trash"></i></button>' : ''}
          </div>
        </div>
        </div>
        ${handle}
      `;
    }

    let control = `<input class="sz_input spv-preview-control" type="text" placeholder="${placeholder}" readonly>`;
    if (type === 'COMBO') {
      control = `
        <select class="sz_select spv-preview-control" disabled>
          <option>${escapeHtml(boundValue || fieldLabel(field))}</option>
        </select>
      `;
    } else if (type === 'DATE') {
      control = `<input class="sz_date spv-preview-control" type="date" value="${escapeHtml(boundValue)}" readonly>`;
    } else if (type === 'HOUR') {
      control = `<input class="sz_input spv-preview-control" type="time" value="${escapeHtml(boundValue)}" readonly>`;
    } else if (type === 'INT') {
      control = `<input class="sz_input_number spv-preview-control" type="number" step="1" value="${escapeHtml(boundValue)}" placeholder="0" readonly>`;
    } else if (type === 'DECIMAL') {
      control = `<input class="sz_input_number spv-preview-control" type="number" step="0.01" value="${escapeHtml(boundValue)}" placeholder="0,00" readonly>`;
    } else if (type === 'MEMO') {
      control = `<textarea class="sz_textarea spv-preview-control" rows="3" readonly placeholder="${placeholder}">${escapeHtml(boundValue)}</textarea>`;
    } else if (type === 'COLOR') {
      const colorValue = /^#?[0-9a-fA-F]{6}$/.test(boundValue) ? (boundValue.startsWith('#') ? boundValue : `#${boundValue}`) : '#4f8cff';
      control = `<input class="sz_input spv-preview-control" type="color" value="${escapeHtml(colorValue)}" readonly>`;
    } else if (type === 'LINK') {
      control = `<input class="sz_input spv-preview-control" type="text" value="${escapeHtml(boundValue)}" placeholder="https://${placeholder.toLowerCase()}" readonly>`;
    } else if (boundValue) {
      control = `<input class="sz_input spv-preview-control" type="text" value="${escapeHtml(boundValue)}" placeholder="${placeholder}" readonly>`;
    }

    return `
      <label class="sz_label">${label}</label>
      ${control}
      ${handle}
    `;
  }

  function buildListPreviewControl(field) {
    const type = detectFieldType(field);
    const meta = TYPE_META[type] || TYPE_META.TEXT;
    return `
      <div class="spv-list-preview-head">
        <span class="spv-list-preview-title">${escapeHtml(fieldLabel(field))}</span>
        <span class="spv-list-preview-type">${escapeHtml(TYPE_LABELS_EN[type] || meta.label || type)}</span>
      </div>
      <div class="spv-list-preview-sample">${escapeHtml(field.NMCAMPO || '')}</div>
      ${buildResizeHandle(field)}
    `;
  }

  function buildListMobilePreviewControl(field) {
    const showLabel = Number(field.LISTA_MOBILE_SHOW_LABEL ?? 1) === 1;
    const label = String(field.LISTA_MOBILE_LABEL || field.DESCRICAO || field.NMCAMPO || '').trim() || fieldLabel(field);
    const valueClasses = ['spv-list-mobile-value'];
    if (Number(field.LISTA_MOBILE_BOLD || 0) === 1) valueClasses.push('is-bold');
    if (Number(field.LISTA_MOBILE_ITALIC || 0) === 1) valueClasses.push('is-italic');
    return `
      <div class="spv-list-mobile-field">
        ${showLabel ? `<div class="spv-list-mobile-label">${escapeHtml(label)}</div>` : ''}
        <div class="${valueClasses.join(' ')}">${escapeHtml(String(field.NMCAMPO || '').trim() || fieldLabel(field))}</div>
      </div>
      ${buildResizeHandle(field)}
    `;
  }

  function getPreviewFrameMeta() {
    if (isListLayoutMode()) {
      if (isMobileMode()) {
        return {
          title: 'Mobile Card',
          subtitle: 'Layout do dynamic_list em modo mobile.',
        };
      }
      return {
        title: 'Desktop List',
        subtitle: 'Layout das colunas do dynamic_list em modo desktop.',
      };
    }
    if (isMobileMode()) {
      return {
        title: 'Mobile Form',
        subtitle: 'Layout do dynamic_form em modo mobile.',
      };
    }
    return {
      title: 'Desktop Form',
      subtitle: 'Layout do dynamic_form em modo desktop.',
    };
  }

  function buildPreviewFrame(content, { mobile = false, panelClass = '', contentClass = '' } = {}) {
    const meta = getPreviewFrameMeta();
    const panelClasses = ['sz_card', 'spv-preview-frame', panelClass].filter(Boolean).join(' ');
    const contentClasses = ['spv-preview-frame-content', contentClass].filter(Boolean).join(' ');
    return `
      <div class="spv-preview-screen ${mobile ? 'is-mobile' : ''}">
        <div class="spv-preview-body">
          <div class="${panelClasses}">
            <div class="spv-preview-frame-head">
              <div class="spv-preview-frame-title">${escapeHtml(meta.title)}</div>
              <div class="spv-preview-frame-subtitle">${escapeHtml(meta.subtitle)}</div>
            </div>
            <div class="${contentClasses}">
              ${content}
            </div>
          </div>
        </div>
      </div>
    `;
  }

  function groupPreviewFields(fields) {
    const groups = new Map();
    getVisibleLayoutFields(fields)
      .forEach((field) => {
        const key = getFieldRowId(field);
        if (!groups.has(key)) groups.set(key, []);
        groups.get(key).push(field);
      });
    return [...groups.entries()].sort((a, b) => a[0] - b[0]);
  }

  function syncPreviewScaleHeight() {
    if (!els.previewStage) return;
    requestAnimationFrame(() => {
      els.previewStage.style.height = '';
    });
  }

  function buildDropPlaceholder(size, { invalid = false } = {}) {
    return `
      <div class="spv-preview-col spv-drop-placeholder-col ${invalid ? 'is-invalid' : ''}" style="grid-column: span ${size};">
        <div class="spv-drop-placeholder ${invalid ? 'is-invalid' : ''}">
          <span>${invalid ? 'Sem espaço' : 'Largar aqui'}</span>
        </div>
      </div>
    `;
  }

  function getRowDragState(rowId) {
    if (!state.drag?.active || String(state.drag.overMode || 'row') !== 'row' || Number(state.drag.overRowId) !== Number(rowId)) return null;
    return state.drag;
  }

  function getGapDragState(rowId) {
    if (!state.drag?.active || String(state.drag.overMode || '') !== 'gap' || Number(state.drag.overRowId) !== Number(rowId)) return null;
    return state.drag;
  }

  function formatNumericPropertyValue(value) {
    if (value === null || value === undefined) return '';
    return String(value).trim();
  }

  function getEventPropertyButtonMarkup({ name = 'Event', eventName = 'click', configured = false } = {}) {
    const statusLabel = configured ? 'Evento configurado' : 'Evento nao configurado';
    return `<button
      type="button"
      class="spv-prop-row spv-prop-row-event${configured ? ' is-configured' : ''}"
      data-event-editor="${escapeHtml(eventName)}"
      aria-label="${escapeHtml(`Edit ${name} event`)}"
    >
      <span class="spv-prop-event-trigger">
        <span class="spv-prop-event-main">
          <span class="spv-prop-event-icon" aria-hidden="true">
            <i class="fa-solid fa-diagram-project"></i>
          </span>
          <span class="spv-prop-event-label">${escapeHtml(name)}</span>
        </span>
        <span
          class="spv-prop-event-status${configured ? ' is-configured' : ''}"
          aria-label="${escapeHtml(statusLabel)}"
          title="${escapeHtml(statusLabel)}"
        >
          <i class="fa-solid ${configured ? 'fa-bolt' : 'fa-circle'}" aria-hidden="true"></i>
        </span>
      </span>
    </button>`;
  }

  function renderScreenProperties() {
    if (!els.propertiesContent) return;
    const menu = getScreenMenu();
    const hasScreen = !!String(menu.MENUSTAMP || '').trim();
    if (!hasScreen) {
      els.propertiesContent.innerHTML = `
        <div class="spv-field-icon"><i class="fa-solid fa-window-maximize"></i></div>
        <div class="sz_text_muted">Seleciona um ecrã para ver as propriedades.</div>
      `;
      return;
    }

    const props = [
      { name: 'Screen', value: String(menu.NOME || menu.TABELA || 'Screen').trim() || 'Screen' },
      { name: 'Table', value: String(menu.TABELA || '').trim() || '-' },
      { name: 'Url', value: String(menu.URL || '').trim() || '-' },
      { name: 'Layout', value: isListLayoutMode() ? 'List' : 'Form' },
      { name: 'Width Mode', value: state.useExactWidths ? 'Exact widths' : 'Proportional widths' },
      { name: 'Init', eventName: 'init' },
      { name: 'Before Save', eventName: 'before_save' },
      { name: 'Before Delete', eventName: 'before_delete' },
    ];

    els.propertiesContent.innerHTML = `
      <div class="spv-prop-grid">
        ${props.map((prop) => (
          prop.eventName
            ? getEventPropertyButtonMarkup({
                name: prop.name,
                eventName: prop.eventName,
                configured: hasMenuEventConfigured(menu, prop.eventName),
              })
            : `<div class="spv-prop-row">
                <div class="spv-prop-name">${escapeHtml(prop.name)}</div>
                <div class="spv-prop-value">${escapeHtml(prop.value)}</div>
              </div>`
        )).join('')}
      </div>
    `;
  }

  function renderVariableProperties() {
    if (!els.propertiesContent) return;
    ensureSelectedVariable();
    const variable = findVariableByStamp(state.selectedVariableStamp);
    if (!variable) {
      els.propertiesContent.innerHTML = `
        <div class="spv-field-icon"><i class="fa-solid fa-code"></i></div>
        <div class="sz_text_muted">Cria uma variavel no separador "+" para ela aparecer aqui.</div>
      `;
      return;
    }
    const meta = getVariableTypeMeta(variable.TIPO);
    const help = variableHelpText(variable);
    els.propertiesContent.innerHTML = `
      <div class="spv-prop-grid">
        <div class="spv-prop-row">
          <div class="spv-prop-name">Descricao</div>
          <div class="spv-prop-value">${escapeHtml(variableLabel(variable))}</div>
        </div>
        <div class="spv-prop-row">
          <div class="spv-prop-name">Nome interno</div>
          <div class="spv-prop-value">${escapeHtml(variable.NOME || '')}</div>
        </div>
        <div class="spv-prop-row">
          <div class="spv-prop-name">Tipo</div>
          <div class="spv-prop-value">${escapeHtml(meta.label)}</div>
        </div>
        <div class="spv-prop-row">
          <div class="spv-prop-name">Default</div>
          <div class="spv-prop-value">${escapeHtml(String(variable.VALOR_DEFAULT || '').trim() || '-')}</div>
        </div>
        <div class="spv-prop-row">
          <div class="spv-prop-name">Ajuda</div>
          <div class="spv-prop-value">${escapeHtml(help || '-')}</div>
        </div>
        <div class="spv-variable-actions">
          <button type="button" class="sz_button sz_button_secondary" data-variable-action="edit-selected">
            <i class="fa-solid fa-pen"></i>
            <span>Editar</span>
          </button>
          <button type="button" class="sz_button sz_button_ghost" data-variable-action="delete-selected">
            <i class="fa-solid fa-trash"></i>
            <span>Eliminar</span>
          </button>
        </div>
      </div>
    `;
  }

  function renderProperties() {
    if (!els.propertiesContent) return;
    if (state.selectedScope === 'variable') {
      renderVariableProperties();
      return;
    }
    if (state.selectedScope === 'screen') {
      renderScreenProperties();
      return;
    }
    ensureSelectedField();
    const field = findKnownFieldByStamp(state.selectedFieldStamp);
    if (!field) {
      els.propertiesContent.innerHTML = `
        <div class="spv-field-icon"><i class="fa-solid fa-sliders"></i></div>
        <div class="sz_text_muted">Clica num campo no visualizador para ver as propriedades.</div>
      `;
      return;
    }
    const fieldType = detectFieldType(field);
    let originValue = 'Field';
    const origin = String(field._SPV_ORIGIN || 'field').toLowerCase();
    if (origin === 'object') originValue = 'Object';
    if (origin === 'sql') originValue = 'SQL column';
    const isButton = fieldType === 'BUTTON';
    const listMode = isListLayoutMode();
    const listMobileMode = isListMobileLayoutMode();
    const editableName = isCustomObject(field);
    const canBindVariable = isCustomObject(field) && !['SPACE', 'BUTTON', 'TABLE'].includes(fieldType);
    const boundVariable = getFieldBoundVariable(field);
    const fieldProps = getFieldProperties(field);
    const tableSourceType = String(fieldProps.source_type || 'sql_table').trim() || 'sql_table';
    const sqlTableOptions = state.sqlTables.length
      ? state.sqlTables.map((table) => ({
          value: String(table.key || '').trim(),
          label: String(table.label || table.key || '').trim(),
        }))
      : [{ value: '', label: 'Sem tabelas disponiveis' }];
    const lineValue = listMode
      ? (listMobileMode
        ? (Number(field.ORDEM_LISTA_MOBILE || 0) > 0 ? `Row ${Math.max(1, Number(field._SPV_ROW_LIST_MOBILE || getFieldRowId(field) || 1))} · Pos ${Math.max(1, Number(field._SPV_POS_LIST_MOBILE ?? getFieldPos(field)) + 1)}` : 'Out of mobile card')
        : (Number(field.LISTA || 0) === 1 ? String((Number(field._SPV_POS_LIST ?? -1) + 1) || 1) : 'Out of list'))
      : (isVisibleField(field) ? String(getFieldRowId(field) || 1) : 'Out of layout');
    const showNumericRange = fieldType === 'INT' || fieldType === 'DECIMAL';
    const showDecimals = fieldType === 'DECIMAL';
    const props = [
      {
        name: 'Text',
        value: String(field.DESCRICAO || '').trim() || fieldLabel(field),
        editor: 'DESCRICAO',
      },
      {
        name: 'Name',
        value: String(field.NMCAMPO || '').trim() || fieldLabel(field),
        editor: editableName ? 'NMCAMPO' : '',
      },
      { name: 'Origin', value: originValue },
      { name: 'Type', value: TYPE_LABELS_EN[fieldType] || fieldType },
      { name: 'Width', value: `${Number(field?.[getActiveWidthField()] || 0)}%` },
      { name: listMode ? (listMobileMode ? 'Placement' : 'Position') : 'Line', value: lineValue },
      {
        name: listMode ? (listMobileMode ? 'In Mobile Card' : 'In List') : 'Visible',
        value: listMode
          ? (listMobileMode ? (Number(field.ORDEM_LISTA_MOBILE || 0) > 0 ? 'Yes' : 'No') : (Number(field.LISTA || 0) ? 'Yes' : 'No'))
          : (Number(field.VISIVEL ?? 1) ? 'Yes' : 'No'),
        editor: listMode ? (listMobileMode ? 'LISTA_MOBILE_VISIBLE' : 'LISTA') : 'VISIVEL',
        editorType: 'boolean',
      },
    ];
    if (listMobileMode) {
      props.push(
        {
          name: 'Show Label',
          value: Number(field.LISTA_MOBILE_SHOW_LABEL ?? 1) ? 'Yes' : 'No',
          editor: 'LISTA_MOBILE_SHOW_LABEL',
          editorType: 'boolean',
        },
        {
          name: 'Label',
          value: String(field.LISTA_MOBILE_LABEL || field.DESCRICAO || field.NMCAMPO || '').trim(),
          editor: 'LISTA_MOBILE_LABEL',
        },
        {
          name: 'Bold',
          value: Number(field.LISTA_MOBILE_BOLD || 0) ? 'Yes' : 'No',
          editor: 'LISTA_MOBILE_BOLD',
          editorType: 'boolean',
        },
        {
          name: 'Italic',
          value: Number(field.LISTA_MOBILE_ITALIC || 0) ? 'Yes' : 'No',
          editor: 'LISTA_MOBILE_ITALIC',
          editorType: 'boolean',
        },
      );
    }
    if (isButton) {
      props.push(
        {
          name: 'Enabled',
          value: isFieldEnabled(field) ? 'Yes' : 'No',
          editor: 'BUTTON_ENABLED',
          editorType: 'boolean',
          editorValue: isFieldEnabled(field) ? '1' : '0',
        },
        {
          name: 'Click',
          value: getFieldEventSummary(field, 'click'),
          editor: 'BUTTON_CLICK',
          editorType: 'event',
          configured: hasFieldEventConfigured(field, 'click'),
          actionLabel: 'Abrir editor',
          eventName: 'click',
          helperText: hasFieldLegacyScript(field, 'click')
            ? 'Existe um script JS legado neste evento. O editor visual nao o converte automaticamente.'
            : 'O evento passa a ser desenhado por comandos visuais e pseudo-codigo.',
        },
      );
    } else if (!listMode && fieldType !== 'TABLE') {
      props.push(
        {
          name: 'Required',
          value: Number(field.OBRIGATORIO || 0) ? 'Yes' : 'No',
          editor: 'OBRIGATORIO',
          editorType: 'boolean',
        },
        {
          name: 'Read only',
          value: Number(field.RONLY || 0) ? 'Yes' : 'No',
          editor: 'RONLY',
          editorType: 'boolean',
        },
      );
    }
    if (!listMode && fieldType === 'TABLE') {
      props.push(
        {
          name: 'Source Type',
          value: tableSourceType,
          editor: 'TABLE_SOURCE_TYPE',
          editorType: 'select',
          options: [
            { value: 'sql_table', label: 'SQL Table' },
            { value: 'cursor', label: 'Cursor' },
          ],
        },
        (
          tableSourceType === 'cursor'
            ? {
                name: 'Source',
                value: String(fieldProps.source || '').trim(),
                editor: 'TABLE_SOURCE',
              }
            : {
                name: 'Source',
                value: String(fieldProps.source || '').trim(),
                editor: 'TABLE_SOURCE',
                editorType: 'select',
                options: [{ value: '', label: 'Seleciona uma tabela' }, ...sqlTableOptions],
              }
        ),
        {
          name: 'Field Link',
          value: String(fieldProps.field_link || '').trim(),
          editor: 'TABLE_FIELD_LINK',
        },
        {
          name: 'Source Link',
          value: String(fieldProps.source_link || '').trim(),
          editor: 'TABLE_SOURCE_LINK',
        },
        {
          name: 'Show Add Button',
          value: isTruthyLike(fieldProps.show_add_button) ? 'Yes' : 'No',
          editor: 'TABLE_SHOW_ADD_BUTTON',
          editorType: 'boolean',
          editorValue: isTruthyLike(fieldProps.show_add_button) ? '1' : '0',
        },
        {
          name: 'Show Delete Button',
          value: isTruthyLike(fieldProps.show_delete_button) ? 'Yes' : 'No',
          editor: 'TABLE_SHOW_DELETE_BUTTON',
          editorType: 'boolean',
          editorValue: isTruthyLike(fieldProps.show_delete_button) ? '1' : '0',
        },
      );
    }
    if (!listMode && canBindVariable) {
      props.push({
        name: 'Variable',
        value: boundVariable ? boundVariable.NOME : '',
        editor: 'VARIABLE_NAME',
        editorType: 'select',
        options: [
          { value: '', label: getScreenVariables().length ? 'Sem variavel' : 'Sem variaveis disponiveis' },
          ...sortVariablesForList(getScreenVariables()).map((variable) => ({
            value: normalizeVariableName(variable.NOME),
            label: `${variable.NOME} · ${getVariableTypeMeta(variable.TIPO).label}`,
          })),
        ],
      });
      if (boundVariable) {
        props.push(
          {
            name: 'Variable default',
            value: String(boundVariable.VALOR_DEFAULT || '').trim() || '-',
          },
          {
            name: 'Variable help',
            value: variableHelpText(boundVariable) || '-',
          },
        );
      }
    }
    if (showNumericRange) {
      props.push(
        {
          name: 'Minimum',
          value: formatNumericPropertyValue(field.MINIMO),
          editor: 'MINIMO',
          editorType: 'number',
          step: fieldType === 'INT' ? '1' : 'any',
        },
        {
          name: 'Maximum',
          value: formatNumericPropertyValue(field.MAXIMO),
          editor: 'MAXIMO',
          editorType: 'number',
          step: fieldType === 'INT' ? '1' : 'any',
        },
      );
    }
    if (showDecimals) {
      props.push({
        name: 'Decimals',
        value: String(Number(field.DECIMAIS || 0)),
        editor: 'DECIMAIS',
        editorType: 'number',
        step: '1',
        min: '0',
      });
    }
    els.propertiesContent.innerHTML = `
      <div class="spv-prop-grid">
        ${props.map((prop) => `
          ${prop.editorType === 'event'
            ? getEventPropertyButtonMarkup({
                name: prop.name,
                eventName: prop.eventName || prop.editor,
                configured: Boolean(prop.configured),
              })
            : `<div class="spv-prop-row">
                <div class="spv-prop-name">${escapeHtml(prop.name)}</div>
                ${prop.editorType === 'boolean'
              ? `<select class="sz_select spv-prop-select" data-prop-editor="${escapeHtml(prop.editor)}">
                  <option value="1" ${Number(prop.editorValue ?? field[prop.editor] ?? (prop.editor === 'VISIVEL' ? 1 : 0)) ? 'selected' : ''}>Yes</option>
                  <option value="0" ${Number(prop.editorValue ?? field[prop.editor] ?? (prop.editor === 'VISIVEL' ? 1 : 0)) ? '' : 'selected'}>No</option>
                </select>`
              : prop.editorType === 'select'
              ? `<select class="sz_select spv-prop-select" data-prop-editor="${escapeHtml(prop.editor)}">
                  ${(Array.isArray(prop.options) ? prop.options : []).map((option) => `
                    <option value="${escapeHtml(option.value)}" ${String(prop.value || '') === String(option.value || '') ? 'selected' : ''}>${escapeHtml(option.label)}</option>
                  `).join('')}
                </select>`
              : prop.editorType === 'textarea'
              ? `<textarea class="sz_textarea spv-prop-input" rows="${escapeHtml(String(prop.rows || 4))}" data-prop-editor="${escapeHtml(prop.editor)}" placeholder="${escapeHtml(prop.placeholder || '')}">${escapeHtml(prop.value || '')}</textarea>`
              : prop.editorType === 'number'
              ? `<input type="number" class="sz_input spv-prop-input" data-prop-editor="${escapeHtml(prop.editor)}" value="${escapeHtml(prop.value)}"${prop.step ? ` step="${escapeHtml(prop.step)}"` : ''}${prop.min ? ` min="${escapeHtml(prop.min)}"` : ''}>`
              : prop.editor
              ? `<input type="text" class="sz_input spv-prop-input" data-prop-editor="${escapeHtml(prop.editor)}" value="${escapeHtml(prop.value)}">`
              : `<div class="spv-prop-value">${escapeHtml(prop.value)}</div>`}
              </div>`}
        `).join('')}
      </div>
    `;
  }

  function updateSelectedFieldProperty(propName, nextValue) {
    const field = findFieldByStamp(state.selectedFieldStamp);
    if (!field) return;
    const value = String(nextValue ?? '').trim();
    if (propName === 'DESCRICAO') {
      field.DESCRICAO = value || (String(field.NMCAMPO || '').trim() || fieldLabel(field));
    } else if (propName === 'NMCAMPO') {
      if (!isCustomObject(field)) return;
      field.NMCAMPO = value || String(field.NMCAMPO || '').trim() || 'OBJECT';
    } else if (propName === 'VISIVEL') {
      field.VISIVEL = Number(nextValue) ? 1 : 0;
    } else if (propName === 'LISTA') {
      if (Number(nextValue)) {
        moveFieldToList(getFieldStamp(field), getVisibleListFields().length);
      } else {
        applyListFieldSequence(getVisibleListFields({ excludeStamp: getFieldStamp(field) }));
      }
    } else if (propName === 'LISTA_MOBILE_VISIBLE') {
      toggleFieldInListMobile(getFieldStamp(field), Number(nextValue) === 1);
    } else if (propName === 'OBRIGATORIO') {
      field.OBRIGATORIO = Number(nextValue) ? 1 : 0;
    } else if (propName === 'RONLY') {
      field.RONLY = Number(nextValue) ? 1 : 0;
    } else if (propName === 'LISTA_MOBILE_BOLD') {
      field.LISTA_MOBILE_BOLD = Number(nextValue) ? 1 : 0;
    } else if (propName === 'LISTA_MOBILE_ITALIC') {
      field.LISTA_MOBILE_ITALIC = Number(nextValue) ? 1 : 0;
    } else if (propName === 'LISTA_MOBILE_SHOW_LABEL') {
      field.LISTA_MOBILE_SHOW_LABEL = Number(nextValue) ? 1 : 0;
    } else if (propName === 'LISTA_MOBILE_LABEL') {
      field.LISTA_MOBILE_LABEL = value || String(field.DESCRICAO || field.NMCAMPO || '').trim();
    } else if (propName === 'BUTTON_ENABLED') {
      if (detectFieldType(field) !== 'BUTTON') return;
      if (!field.PROPRIEDADES || typeof field.PROPRIEDADES !== 'object') {
        field.PROPRIEDADES = {};
      }
      field.PROPRIEDADES.enabled = Number(nextValue) ? 1 : 0;
    } else if (propName === 'BUTTON_CLICK') {
      if (detectFieldType(field) !== 'BUTTON') return;
      if (!field.PROPRIEDADES || typeof field.PROPRIEDADES !== 'object') {
        field.PROPRIEDADES = {};
      }
      if (value) {
        field.PROPRIEDADES.click_action = value;
      } else {
        delete field.PROPRIEDADES.click_action;
      }
    } else if (propName === 'VARIABLE_NAME') {
      if (!isCustomObject(field)) return;
      if (!field.PROPRIEDADES || typeof field.PROPRIEDADES !== 'object') {
        field.PROPRIEDADES = {};
      }
      const variableName = normalizeVariableName(nextValue);
      if (variableName) {
        field.PROPRIEDADES.variable_name = variableName;
      } else {
        delete field.PROPRIEDADES.variable_name;
      }
    } else if (propName === 'TABLE_SOURCE_TYPE') {
      if (detectFieldType(field) !== 'TABLE') return;
      if (!field.PROPRIEDADES || typeof field.PROPRIEDADES !== 'object') {
        field.PROPRIEDADES = {};
      }
      field.PROPRIEDADES.source_type = value === 'cursor' ? 'cursor' : 'sql_table';
    } else if (propName === 'TABLE_SOURCE') {
      if (detectFieldType(field) !== 'TABLE') return;
      if (!field.PROPRIEDADES || typeof field.PROPRIEDADES !== 'object') {
        field.PROPRIEDADES = {};
      }
      if (value) {
        field.PROPRIEDADES.source = value;
      } else {
        delete field.PROPRIEDADES.source;
      }
    } else if (propName === 'TABLE_FIELD_LINK') {
      if (detectFieldType(field) !== 'TABLE') return;
      if (!field.PROPRIEDADES || typeof field.PROPRIEDADES !== 'object') {
        field.PROPRIEDADES = {};
      }
      if (value) {
        field.PROPRIEDADES.field_link = value;
      } else {
        delete field.PROPRIEDADES.field_link;
      }
    } else if (propName === 'TABLE_SOURCE_LINK') {
      if (detectFieldType(field) !== 'TABLE') return;
      if (!field.PROPRIEDADES || typeof field.PROPRIEDADES !== 'object') {
        field.PROPRIEDADES = {};
      }
      if (value) {
        field.PROPRIEDADES.source_link = value;
      } else {
        delete field.PROPRIEDADES.source_link;
      }
    } else if (propName === 'TABLE_SHOW_ADD_BUTTON') {
      if (detectFieldType(field) !== 'TABLE') return;
      if (!field.PROPRIEDADES || typeof field.PROPRIEDADES !== 'object') {
        field.PROPRIEDADES = {};
      }
      field.PROPRIEDADES.show_add_button = Number(nextValue) ? 1 : 0;
    } else if (propName === 'TABLE_SHOW_DELETE_BUTTON') {
      if (detectFieldType(field) !== 'TABLE') return;
      if (!field.PROPRIEDADES || typeof field.PROPRIEDADES !== 'object') {
        field.PROPRIEDADES = {};
      }
      field.PROPRIEDADES.show_delete_button = Number(nextValue) ? 1 : 0;
    } else if (propName === 'DECIMAIS') {
      field.DECIMAIS = Math.max(0, Number.parseInt(String(nextValue || '').trim(), 10) || 0);
    } else if (propName === 'MINIMO' || propName === 'MAXIMO') {
      field[propName] = formatNumericPropertyValue(nextValue);
    } else {
      return;
    }
    renderSidebarList();
    renderPreview();
  }

  function removeSelectedFieldLocally() {
    const field = findKnownFieldByStamp(state.selectedFieldStamp);
    if (!field) return false;
    const stamp = getFieldStamp(field);
    if (isCustomObject(field)) {
      state.customObjects = getScreenObjects().filter((item) => getFieldStamp(item) !== stamp);
      state.selectedFieldStamp = getDefaultFieldStamp();
      state.selectedScope = getDefaultSelectionScope();
      renderAll();
      setStatus(`Ajuste local aplicado: ${fieldLabel(field)} eliminado do ecrã. Nao gravado.`);
      return true;
    }
    if (isListLayoutMode()) {
      if (isListMobileLayoutMode()) {
        toggleFieldInListMobile(stamp, false);
        state.selectedFieldStamp = getDefaultFieldStamp();
        state.selectedScope = getDefaultSelectionScope();
        renderAll();
        setStatus(`Ajuste local aplicado: ${fieldLabel(field)} removido do card mobile. Nao gravado.`);
        return true;
      }
      applyListFieldSequence(getVisibleListFields({ excludeStamp: stamp }));
      state.selectedFieldStamp = getDefaultFieldStamp();
      state.selectedScope = getDefaultSelectionScope();
      renderAll();
      setStatus(`Ajuste local aplicado: ${fieldLabel(field)} removido da lista. Nao gravado.`);
      return true;
    }
    field.ORDEM = 0;
    field.ORDEM_MOBILE = 0;
    field._SPV_ROW = -1;
    field._SPV_POS = 9999;
    field._SPV_ROW_MOBILE = -1;
    field._SPV_POS_MOBILE = 9999;
    normalizeLocalLayout();
    state.selectedFieldStamp = getDefaultFieldStamp();
    state.selectedScope = getDefaultSelectionScope();
    renderAll();
    setStatus(`Ajuste local aplicado: ${fieldLabel(field)} removido do ecrã. Não gravado.`);
    return true;
  }

  async function requestDeleteSelectedField() {
    const field = findKnownFieldByStamp(state.selectedFieldStamp);
    if (!field) return;
    const isObject = isCustomObject(field);
    const message = isObject
      ? `Pretende eliminar o objeto "${fieldLabel(field)}" deste ecrã?`
      : `Pretende remover o campo "${fieldLabel(field)}" deste ecrã?`;
    const confirmed = await confirmDelete(message);
    if (!confirmed) return;
    removeSelectedFieldLocally();
  }

  function getVariableModalInstance() {
    if (!els.variableModal || !window.bootstrap?.Modal) return null;
    return window.bootstrap.Modal.getOrCreateInstance(els.variableModal);
  }

  function updateVariableTypeHint() {
    const meta = getVariableTypeMeta(els.variableType?.value || 'TEXT');
    if (els.variableDefaultHint) {
      els.variableDefaultHint.textContent = meta.hint;
    }
    if (els.variableDefault) {
      els.variableDefault.placeholder = `Default para ${meta.label.toLowerCase()}`;
    }
  }

  function resetVariableModal() {
    if (els.variableForm) els.variableForm.reset();
    if (els.variableStamp) els.variableStamp.value = '';
    if (els.variableName) els.variableName.value = '';
    if (els.variableDescription) els.variableDescription.value = '';
    if (els.variableType) els.variableType.value = 'TEXT';
    if (els.variableDefault) els.variableDefault.value = '';
    if (els.variableHelp) els.variableHelp.value = '';
    if (els.variableModalTitle) els.variableModalTitle.textContent = 'Nova variavel';
    if (els.variableDeleteBtn) els.variableDeleteBtn.classList.add('sz_hidden');
    updateVariableTypeHint();
  }

  function openVariableModal(variableStamp = '') {
    const hasScreen = !!String(state.detail?.menu?.MENUSTAMP || '').trim();
    if (!hasScreen) {
      setStatus('Seleciona um ecra antes de criar variaveis.', 'danger');
      showToast('Seleciona um ecra antes de criar variaveis.', 'error');
      return;
    }
    const variable = findVariableByStamp(variableStamp);
    resetVariableModal();
    if (variable) {
      if (els.variableStamp) els.variableStamp.value = String(variable.VARIAVELSTAMP || '').trim();
      if (els.variableName) els.variableName.value = String(variable.NOME || '').trim();
      if (els.variableDescription) els.variableDescription.value = String(variable.DESCRICAO || '').trim();
      if (els.variableType) els.variableType.value = String(variable.TIPO || 'TEXT').trim().toUpperCase();
      if (els.variableDefault) els.variableDefault.value = String(variable.VALOR_DEFAULT ?? '').trim();
      if (els.variableHelp) els.variableHelp.value = variableHelpText(variable);
      if (els.variableModalTitle) els.variableModalTitle.textContent = 'Editar variavel';
      if (els.variableDeleteBtn) els.variableDeleteBtn.classList.remove('sz_hidden');
      state.selectedVariableStamp = String(variable.VARIAVELSTAMP || '').trim();
    } else {
      state.selectedVariableStamp = '';
    }
    updateVariableTypeHint();
    const modal = getVariableModalInstance();
    if (modal) {
      modal.show();
      return;
    }
    showToast('Bootstrap modal indisponivel nesta pagina.', 'error');
  }

  function closeVariableModal() {
    const modal = getVariableModalInstance();
    modal?.hide?.();
  }

  function collectVariableModalPayload() {
    const currentStamp = String(els.variableStamp?.value || '').trim();
    const existing = findVariableByStamp(currentStamp);
    const variableName = normalizeVariableName(
      (els.variableName?.value || '').trim() || (els.variableDescription?.value || '').trim()
    );
    if (!variableName) {
      throw new Error('Indica um nome interno para a variavel.');
    }
    const duplicate = getScreenVariables().find((item) => {
      const sameStamp = String(item.VARIAVELSTAMP || '').trim() === currentStamp;
      return !sameStamp && normalizeVariableName(item.NOME) === variableName;
    });
    if (duplicate) {
      throw new Error(`Ja existe uma variavel com o nome "${variableName}".`);
    }
    const description = String(els.variableDescription?.value || '').trim() || variableName;
    const type = String(els.variableType?.value || 'TEXT').trim().toUpperCase();
    const helpText = String(els.variableHelp?.value || '').trim();
    return normalizeVariableRow({
      VARIAVELSTAMP: currentStamp || nextVariableStamp(),
      NOME: variableName,
      DESCRICAO: description,
      TIPO: VARIABLE_TYPES.includes(type) ? type : 'TEXT',
      VALOR_DEFAULT: String(els.variableDefault?.value ?? '').trim(),
      ORDEM: Number(existing?.ORDEM || ((getScreenVariables().length + 1) * 10)),
      PROPRIEDADES: {
        ...(existing?.PROPRIEDADES && typeof existing.PROPRIEDADES === 'object' ? existing.PROPRIEDADES : {}),
        help_text: helpText,
      },
    });
  }

  function saveVariableFromModal() {
    const payload = collectVariableModalPayload();
    const existing = findVariableByStamp(payload.VARIAVELSTAMP);
    if (existing) {
      Object.assign(existing, payload);
    } else {
      state.variables.push(payload);
    }
    syncVariableOrder();
    state.selectedVariableStamp = String(payload.VARIAVELSTAMP || '').trim();
    state.selectedScope = 'variable';
    state.sidebarMode = 'variables';
    closeVariableModal();
    renderAll();
    setStatus(`Variavel ${variableLabel(payload)} configurada localmente. Nao gravado.`);
  }

  function removeVariableLocally(variableStamp = state.selectedVariableStamp) {
    const stamp = String(variableStamp || '').trim();
    const variable = findVariableByStamp(stamp);
    if (!variable) return false;
    state.variables = getScreenVariables().filter((item) => String(item.VARIAVELSTAMP || '').trim() !== stamp);
    syncVariableOrder();
    state.selectedVariableStamp = getDefaultVariableStamp();
    state.selectedScope = state.selectedVariableStamp ? 'variable' : getDefaultSelectionScope();
    renderAll();
    setStatus(`Variavel ${variableLabel(variable)} removida localmente. Nao gravado.`);
    return true;
  }

  async function requestDeleteSelectedVariable() {
    const variable = findVariableByStamp(state.selectedVariableStamp);
    if (!variable) return;
    const confirmed = await confirmDelete(`Pretende eliminar a variavel "${variableLabel(variable)}" deste ecra?`);
    if (!confirmed) return;
    closeVariableModal();
    removeVariableLocally(String(variable.VARIAVELSTAMP || '').trim());
  }

  function createDefaultEventFlow() {
    const flow = {
      version: 1,
      source: 'visual-editor',
      lines: [createEventLine({ command: 'START' })],
      pseudo_code: '',
    };
    flow.pseudo_code = buildEventPseudoCode(flow);
    return flow;
  }

  function countMeaningfulEventCommands(flow) {
    const lines = Array.isArray(flow?.lines) ? flow.lines : [];
    return lines.filter((line) => (
      !isEventEmptyLine(line)
      && !['START', 'ELSE', 'ENDIF', 'ENDWHILE', 'ENDFOR', 'ENDCURSOR_SCAN'].includes(String(line.command || '').trim().toUpperCase())
    )).length;
  }

  function getEventEditorModalInstance() {
    if (!els.eventEditorModal || !window.bootstrap?.Modal) return null;
    return window.bootstrap.Modal.getOrCreateInstance(els.eventEditorModal);
  }

  function getEventCommandMeta(command) {
    return EVENT_COMMAND_META[String(command || '').trim().toUpperCase()] || null;
  }

  function getEventEditorField() {
    const stamp = String(state.eventEditor?.targetStamp || '').trim();
    return stamp ? findFieldByStamp(stamp) : null;
  }

  function getEventEditorMenu() {
    return state.eventEditor?.scope === 'screen' ? getScreenMenu() : null;
  }

  function getEventEditorLines() {
    return Array.isArray(state.eventEditor?.flow?.lines) ? state.eventEditor.flow.lines : [];
  }

  function findEventLineById(lineId) {
    const stamp = String(lineId || '').trim();
    if (!stamp) return null;
    return getEventEditorLines().find((line) => String(line?.id || '').trim() === stamp) || null;
  }

  function findEventLineIndex(lineId) {
    const stamp = String(lineId || '').trim();
    return getEventEditorLines().findIndex((line) => String(line?.id || '').trim() === stamp);
  }

  function ensureSelectedEventLine() {
    const current = findEventLineById(state.eventEditor?.selectedLineId);
    if (current) return;
    const firstCommand = getEventEditorLines().find((line) => !isEventEmptyLine(line));
    state.eventEditor.selectedLineId = String(firstCommand?.id || '').trim();
  }

  function eventFieldValue(config, key, fallback = '') {
    return String(config?.[key] ?? fallback).trim();
  }

  function normalizeEventCursorField(entry = {}) {
    const normalizedName = String(entry?.name || '')
      .trim()
      .toUpperCase()
      .replace(/[^A-Z0-9_]+/g, '_')
      .replace(/_+/g, '_')
      .replace(/^_+|_+$/g, '')
      .slice(0, 60);
    const allowedTypes = EVENT_CURSOR_FIELD_TYPES.map((item) => item.value);
    const normalizedType = String(entry?.type || 'TEXT').trim().toUpperCase();
    return {
      name: normalizedName,
      type: allowedTypes.includes(normalizedType) ? normalizedType : 'TEXT',
    };
  }

  function getEventCursorSchema(config, key = 'cursor_fields') {
    const raw = Array.isArray(config?.[key]) ? config[key] : [];
    return raw.map(normalizeEventCursorField);
  }

  function updateSelectedEventCursorSchema(key, updater, { rerenderConfig = true } = {}) {
    const line = findEventLineById(state.eventEditor?.selectedLineId);
    if (!line || isEventEmptyLine(line)) return;
    if (!line.config || typeof line.config !== 'object') {
      line.config = {};
    }
    const current = getEventCursorSchema(line.config, key);
    const next = typeof updater === 'function' ? updater(current.slice()) : current.slice();
    const normalized = Array.isArray(next) ? next.map(normalizeEventCursorField) : [];
    if (normalized.some((entry) => entry.name || entry.type)) {
      line.config[key] = normalized;
    } else {
      delete line.config[key];
    }
    renderEventBuilder();
    if (rerenderConfig) renderEventConfig();
    renderEventCode();
  }

  function getEventCursorNames() {
    const names = new Set();
    getEventEditorLines().forEach((line) => {
      if (isEventEmptyLine(line)) return;
      if (String(line.command || '').trim().toUpperCase() !== 'CURSOR_NEW') return;
      const value = String(line.config?.cursor_name || '').trim();
      if (value) names.add(value);
    });
    return Array.from(names).sort((a, b) => a.localeCompare(b));
  }

  function getEventCursorOptions() {
    return getEventCursorNames().map((name) => ({
      value: name,
      label: name,
    }));
  }

  function getEventCursorSchemaByName(cursorName) {
    const target = String(cursorName || '').trim().toUpperCase();
    if (!target) return [];
    const line = getEventEditorLines().find((item) => (
      !isEventEmptyLine(item)
      && String(item.command || '').trim().toUpperCase() === 'CURSOR_NEW'
      && String(item.config?.cursor_name || '').trim().toUpperCase() === target
    ));
    return line ? getEventCursorSchema(line.config).filter((entry) => entry.name) : [];
  }

  function getEventCursorFieldOptions(cursorName = '') {
    return getEventCursorSchemaByName(cursorName).map((entry) => ({
      value: entry.name,
      label: `${entry.name} · ${TYPE_LABELS_EN[entry.type] || entry.type}`,
    }));
  }

  function isEventConfigFieldVisible(line, field) {
    const rule = field?.showWhen;
    if (!rule || typeof rule !== 'object') return true;
    return Object.entries(rule).every(([key, expected]) => {
      const current = String(line?.config?.[key] ?? '').trim();
      if (Array.isArray(expected)) {
        return expected.map((item) => String(item ?? '').trim()).includes(current);
      }
      return current === String(expected ?? '').trim();
    });
  }

  function getEventFieldDisplayValue(line, field) {
    const key = String(field?.key || '').trim();
    if (!key) return '';
    if (key === 'cursor_fields') {
      return getEventCursorSchema(line?.config, key)
        .filter((entry) => entry.name)
        .map((entry) => `${entry.name} ${TYPE_LABELS_EN[entry.type] || entry.type}`)
        .join(', ');
    }
    if (key === 'sql_query') {
      const compact = eventFieldValue(line?.config, key).replace(/\s+/g, ' ').trim();
      if (compact.length <= 72) return compact;
      return `${compact.slice(0, 69)}...`;
    }
    return eventFieldValue(line?.config, key);
  }

  function eventFieldPairs(line) {
    const meta = getEventCommandMeta(line?.command);
    if (!meta) return [];
    return (Array.isArray(meta.fields) ? meta.fields : [])
      .map((field) => {
        const value = getEventFieldDisplayValue(line, field);
        if (!value) return '';
        return `${getEventFieldLabel(field)}: ${value}`;
      })
      .filter(Boolean);
  }

  function buildEventLineSummary(line, { mode = 'builder' } = {}) {
    if (isEventEmptyLine(line)) {
      return '';
    }
    const meta = getEventCommandMeta(line.command);
    if (!meta) return String(line.command || '').trim().toUpperCase();
    const values = eventFieldPairs(line);
    const summary = values.join(mode === 'pseudo' ? ' | ' : ' · ');
    const cmd = String(line.command || '').trim().toUpperCase();
    if (cmd === 'START') return mode === 'pseudo' ? 'START' : 'Inicio do fluxo';
    if (cmd === 'IF') {
      const condition = eventFieldValue(line.config, 'condition', '<condicao>');
      return mode === 'pseudo' ? `IF ${condition}` : `Condicao: ${condition}`;
    }
    if (cmd === 'ELSE') return mode === 'pseudo' ? 'ELSE' : 'Ramo alternativo';
    if (cmd === 'ENDIF') return mode === 'pseudo' ? 'ENDIF' : 'Fim do IF';
    if (cmd === 'WHILE') {
      const condition = eventFieldValue(line.config, 'condition', '<condicao>');
      return mode === 'pseudo' ? `WHILE ${condition}` : `Condicao: ${condition}`;
    }
    if (cmd === 'ENDWHILE') return mode === 'pseudo' ? 'ENDWHILE' : 'Fim do WHILE';
    if (cmd === 'FOR_EACH') {
      const itemName = eventFieldValue(line.config, 'item_name', 'item');
      const source = eventFieldValue(line.config, 'source', '<lista>');
      return mode === 'pseudo' ? `FOR EACH ${itemName} IN ${source}` : `Item: ${itemName} · Lista: ${source}`;
    }
    if (cmd === 'ENDFOR') return mode === 'pseudo' ? 'ENDFOR' : 'Fim do FOR EACH';
    if (cmd === 'RETURN') {
      const value = eventFieldValue(line.config, 'value', '<valor>');
      return mode === 'pseudo' ? `RETURN ${value}` : `Valor: ${value}`;
    }
    if (cmd === 'BREAK' || cmd === 'CONTINUE') {
      return mode === 'pseudo' ? cmd : meta.description;
    }
    if (cmd === 'DELAY') {
      const duration = eventFieldValue(line.config, 'duration_ms', '0');
      return mode === 'pseudo' ? `DELAY ${duration}ms` : `Duracao: ${duration} ms`;
    }
    return mode === 'pseudo'
      ? `${meta.label.toUpperCase()}${summary ? ` ${summary}` : ''}`
      : (summary || meta.description || meta.label);
  }

  function buildEventPseudoCode(flow) {
    const normalized = normalizeEventFlow(flow);
    const lines = Array.isArray(normalized.lines) ? normalized.lines : [];
    let indent = 0;
    const pseudoLines = [];
    lines.forEach((line) => {
      if (isEventEmptyLine(line)) {
        pseudoLines.push('');
        return;
      }
      const command = String(line.command || '').trim().toUpperCase();
      if (command === 'ELSE' || isEventBlockCloseCommand(command)) {
        indent = Math.max(0, indent - 1);
      }
      pseudoLines.push(`${'  '.repeat(indent)}${buildEventLineSummary(line, { mode: 'pseudo' })}`);
      if (['IF', 'WHILE', 'FOR_EACH', 'ELSE'].includes(command)) {
        indent += 1;
      }
    });
    return pseudoLines.join('\n').replace(/\n{3,}/g, '\n\n').trim() || 'START';
  }

  function renderEventToolbox() {
    if (!els.eventToolbox) return;
    els.eventToolbox.innerHTML = EVENT_COMMAND_GROUPS.map((group) => `
      <section class="spv-event-group sz_panel">
        <div class="spv-event-group-title">${escapeHtml(group.label)}</div>
        <div class="spv-event-command-list">
          ${(Array.isArray(group.items) ? group.items : []).map((item) => `
            <button
              type="button"
              class="spv-event-command sz_card"
              draggable="true"
              data-event-command="${escapeHtml(item.id)}"
              title="${escapeHtml(item.description || item.label)}"
            >
              <span class="spv-event-command-label">${escapeHtml(item.label)}</span>
              <span class="spv-event-command-desc">${escapeHtml(item.description || '')}</span>
            </button>
          `).join('')}
        </div>
      </section>
    `).join('');
  }

  function buildEventTemplate(command) {
    const code = String(command || '').trim().toUpperCase();
    if (!EVENT_COMMAND_META[code]) return [];
    if (code === 'IF') {
      return [
        createEventLine({ command: 'IF' }),
        createEventLine({ kind: 'empty' }),
        createEventLine({ command: 'ELSE' }),
        createEventLine({ kind: 'empty' }),
        createEventLine({ command: 'ENDIF' }),
      ];
    }
    if (code === 'WHILE') {
      return [
        createEventLine({ command: 'WHILE' }),
        createEventLine({ kind: 'empty' }),
        createEventLine({ command: 'ENDWHILE' }),
      ];
    }
    if (code === 'FOR_EACH') {
      return [
        createEventLine({ command: 'FOR_EACH' }),
        createEventLine({ kind: 'empty' }),
        createEventLine({ command: 'ENDFOR' }),
      ];
    }
    if (code === 'CURSOR_SCAN') {
      return [
        createEventLine({ command: 'CURSOR_SCAN', config: { row_name: 'ROW' } }),
        createEventLine({ kind: 'empty' }),
        createEventLine({ command: 'ENDCURSOR_SCAN' }),
      ];
    }
    if (code === 'CURSOR_NEW') {
      return [createEventLine({ command: 'CURSOR_NEW', config: { cursor_mode: 'manual' } })];
    }
    if (code === 'ELSE') {
      return [
        createEventLine({ command: 'ELSE' }),
        createEventLine({ kind: 'empty' }),
      ];
    }
    return [createEventLine({ command: code })];
  }

  function clearEventDropMarkers() {
    els.eventBuilder?.classList.remove('is-over', 'is-over-before', 'is-over-after');
    els.eventBuilder?.querySelectorAll('.is-over, .is-over-before, .is-over-after').forEach((item) => {
      item.classList.remove('is-over', 'is-over-before', 'is-over-after');
    });
  }

  function normalizeEventDraftLines() {
    if (!state.eventEditor?.flow) return;
    const lines = getEventEditorLines()
      .map(createEventLine)
      .filter((line) => line.kind === 'empty' || EVENT_COMMAND_META[line.command]);
    const collapsed = [];
    lines.forEach((line) => {
      if (isEventEmptyLine(line) && isEventEmptyLine(collapsed[collapsed.length - 1])) return;
      collapsed.push(line);
    });
    state.eventEditor.flow.lines = collapsed.length ? collapsed : [createEventLine({ command: 'START' })];
  }

  function insertEventCommandAt(index, command, { replaceEmpty = false } = {}) {
    if (!state.eventEditor?.flow) return;
    const nextLines = buildEventTemplate(command);
    if (!nextLines.length) return;
    const draftLines = getEventEditorLines();
    const safeIndex = Math.max(0, Math.min(Number(index) || 0, draftLines.length));
    if (replaceEmpty && isEventEmptyLine(draftLines[safeIndex])) {
      draftLines.splice(safeIndex, 1, ...nextLines);
    } else {
      draftLines.splice(safeIndex, 0, ...nextLines);
    }
    normalizeEventDraftLines();
    const firstCommand = nextLines.find((line) => !isEventEmptyLine(line));
    state.eventEditor.selectedLineId = String(firstCommand?.id || '').trim();
    renderEventEditor();
  }

  function findEventBlockRange(lines, startIndex) {
    const source = Array.isArray(lines) ? lines : [];
    const current = source[startIndex];
    const opener = String(current?.command || '').trim().toUpperCase();
    const closer = opener === 'IF'
      ? 'ENDIF'
      : opener === 'WHILE'
      ? 'ENDWHILE'
      : opener === 'FOR_EACH'
      ? 'ENDFOR'
      : opener === 'CURSOR_SCAN'
      ? 'ENDCURSOR_SCAN'
      : '';
    if (!closer) return { start: startIndex, end: startIndex };
    let depth = 0;
    for (let i = startIndex + 1; i < source.length; i += 1) {
      const command = String(source[i]?.command || '').trim().toUpperCase();
      if (command === opener) {
        depth += 1;
        continue;
      }
      if (command === closer) {
        if (depth === 0) {
          return { start: startIndex, end: i };
        }
        depth -= 1;
      }
    }
    return { start: startIndex, end: startIndex };
  }

  function removeSelectedEventLine() {
    if (!state.eventEditor?.flow) return;
    const lineIndex = findEventLineIndex(state.eventEditor.selectedLineId);
    if (lineIndex < 0) return;
    const lines = getEventEditorLines();
    const selected = lines[lineIndex];
    const command = String(selected?.command || '').trim().toUpperCase();
    if (['ELSE', 'ENDIF', 'ENDWHILE', 'ENDFOR', 'ENDCURSOR_SCAN'].includes(command)) return;
    const range = isEventBlockOpenCommand(command)
      ? findEventBlockRange(lines, lineIndex)
      : { start: lineIndex, end: lineIndex };
    lines.splice(range.start, (range.end - range.start) + 1);
    normalizeEventDraftLines();
    const fallback = getEventEditorLines()[Math.max(0, range.start - 1)] || getEventEditorLines()[0] || null;
    state.eventEditor.selectedLineId = String(fallback?.id || '').trim();
    renderEventEditor();
  }

  function renderEventBuilder() {
    if (!els.eventBuilder) return;
    const lines = getEventEditorLines();
    const parts = ['<div class="spv-event-gap" data-event-slot-index="0"></div>'];
    lines.forEach((line, index) => {
      if (isEventEmptyLine(line)) {
        parts.push(`<div class="spv-event-gap spv-event-gap-blank" data-event-slot-index="${index}" data-event-replace-empty="1"></div>`);
      } else {
        parts.push(`
          <button
            type="button"
            class="spv-event-line sz_card${String(state.eventEditor?.selectedLineId || '') === String(line.id || '') ? ' is-selected' : ''}${isEventStructuralCommand(line.command) ? ' is-structural' : ''}"
            data-event-line-id="${escapeHtml(line.id || '')}"
          >
            <span class="spv-event-line-body">
              <span class="spv-event-line-title">${escapeHtml(getEventCommandMeta(line.command)?.label || line.command)}</span>
              <span class="spv-event-line-summary">${escapeHtml(buildEventLineSummary(line))}</span>
            </span>
          </button>
        `);
      }
      parts.push(`<div class="spv-event-gap" data-event-slot-index="${index + 1}"></div>`);
    });
    els.eventBuilder.innerHTML = parts.join('');
  }

  function renderEventCursorFieldsMarkup(field, line) {
    const key = String(field?.key || 'cursor_fields').trim();
    const schema = getEventCursorSchema(line?.config, key);
    return `
      <div class="spv-event-cursor-schema" data-event-cursor-schema="${escapeHtml(key)}">
        <div class="spv-event-cursor-schema-list">
          ${schema.length
            ? schema.map((entry, index) => `
                <div class="spv-event-cursor-schema-row" data-event-cursor-schema-index="${index}">
                  <input
                    type="text"
                    class="sz_input"
                    value="${escapeHtml(entry.name)}"
                    placeholder="FIELD_NAME"
                    data-event-cursor-schema-name="${escapeHtml(key)}"
                    data-event-cursor-schema-index="${index}"
                  >
                  <select
                    class="sz_select"
                    data-event-cursor-schema-type="${escapeHtml(key)}"
                    data-event-cursor-schema-index="${index}"
                  >
                    ${EVENT_CURSOR_FIELD_TYPES.map((option) => `
                      <option value="${escapeHtml(option.value)}" ${option.value === entry.type ? 'selected' : ''}>${escapeHtml(option.label)}</option>
                    `).join('')}
                  </select>
                  <button
                    type="button"
                    class="sz_button sz_button_ghost spv-event-cursor-schema-remove"
                    data-event-cursor-remove="${escapeHtml(key)}"
                    data-event-cursor-schema-index="${index}"
                    aria-label="Remove cursor field"
                  >
                    <i class="fa-solid fa-trash"></i>
                  </button>
                </div>
              `).join('')
            : '<div class="spv-event-note">Add the fields that belong to this cursor.</div>'}
        </div>
        <button type="button" class="sz_button sz_button_secondary" data-event-cursor-add="${escapeHtml(key)}">
          <i class="fa-solid fa-plus"></i>
          <span>Add field</span>
        </button>
      </div>
    `;
  }

  function renderEventConfig() {
    if (!els.eventConfig) return;
    ensureSelectedEventLine();
    const line = findEventLineById(state.eventEditor?.selectedLineId);
    if (!line) {
      els.eventConfig.innerHTML = '<div class="spv-event-note">Seleciona um passo do algoritmo para configurar as propriedades.</div>';
      return;
    }
    if (isEventEmptyLine(line)) {
      els.eventConfig.innerHTML = '<div class="spv-event-note">Esta linha esta vazia. Arrasta um comando para ocupar este espaco.</div>';
      return;
    }
    const meta = getEventCommandMeta(line.command);
    const command = String(line.command || '').trim().toUpperCase();
    const fields = Array.isArray(meta?.fields) ? meta.fields : [];
    const isAutoMarker = ['ELSE', 'ENDIF', 'ENDWHILE', 'ENDFOR'].includes(command);
    if (isAutoMarker) {
      els.eventConfig.innerHTML = `
        <div class="spv-event-note">
          Este marcador faz parte da estrutura do algoritmo e e gerado pelo editor.
          Para o remover, elimina o bloco onde ele foi criado.
        </div>
      `;
      return;
    }
    els.eventConfig.innerHTML = `
      <div class="spv-event-config-grid">
        ${fields.map((field) => {
          const value = eventFieldValue(line.config, field.key);
          const spanClass = field.type === 'textarea' ? ' spv-event-config-span' : '';
          return `
            <div class="sz_field${spanClass}">
              <label class="sz_label" for="spvEventConfig_${escapeHtml(field.key)}">${escapeHtml(field.label)}</label>
              ${field.type === 'textarea'
                ? `<textarea id="spvEventConfig_${escapeHtml(field.key)}" class="sz_textarea" rows="${escapeHtml(String(field.rows || 3))}" data-event-config-key="${escapeHtml(field.key)}" placeholder="${escapeHtml(field.placeholder || '')}">${escapeHtml(value)}</textarea>`
                : field.type === 'number'
                ? `<input id="spvEventConfig_${escapeHtml(field.key)}" type="number" class="sz_input" data-event-config-key="${escapeHtml(field.key)}" value="${escapeHtml(value)}"${field.step ? ` step="${escapeHtml(field.step)}"` : ''}${field.min ? ` min="${escapeHtml(field.min)}"` : ''} placeholder="${escapeHtml(field.placeholder || '')}">`
                : field.type === 'select'
                ? `<select id="spvEventConfig_${escapeHtml(field.key)}" class="sz_select" data-event-config-key="${escapeHtml(field.key)}">
                    ${(Array.isArray(field.options) ? field.options : []).map((option) => `
                      <option value="${escapeHtml(option.value)}" ${String(option.value || '') === value ? 'selected' : ''}>${escapeHtml(option.label)}</option>
                    `).join('')}
                  </select>`
                : `<input id="spvEventConfig_${escapeHtml(field.key)}" type="text" class="sz_input" data-event-config-key="${escapeHtml(field.key)}" value="${escapeHtml(value)}" placeholder="${escapeHtml(field.placeholder || '')}">`}
            </div>
          `;
        }).join('')}
      </div>
      <div class="spv-event-config-actions">
        <button type="button" class="sz_button sz_button_ghost" data-event-action="remove-step">
          <i class="fa-solid fa-trash"></i>
          <span>${isEventBlockOpenCommand(command) ? 'Remover bloco' : 'Remover passo'}</span>
        </button>
      </div>
      <div class="spv-event-note">${escapeHtml(meta?.description || '')}</div>
    `;
  }

  function getEventSelectableFields({ includeButtons = false } = {}) {
    return getLayoutItems()
      .map(normalizeCampoRow)
      .filter((field) => {
        const type = detectFieldType(field);
        if (type === 'SPACE') return false;
        if (type === 'TABLE') return false;
        if (!includeButtons && type === 'BUTTON') return false;
        return true;
      })
      .sort(compareLayoutFields);
  }

  function getEventSelectableFieldOptions({ includeButtons = false } = {}) {
    return getEventSelectableFields({ includeButtons }).map((field) => ({
      value: String(field.NMCAMPO || '').trim(),
      label: `${fieldLabel(field)} · ${String(field.NMCAMPO || '').trim()}`,
    }));
  }

  function usesScreenFieldSelect(command, fieldKey) {
    const cmd = String(command || '').trim().toUpperCase();
    const key = String(fieldKey || '').trim();
    if (key === 'field_name') {
      return ['GET_FIELD', 'SET_FIELD', 'FOCUS_FIELD', 'SET_REQUIRED', 'VALIDATE_FIELD'].includes(cmd);
    }
    if (key === 'target') {
      return ['SHOW_HIDE', 'ENABLE_DISABLE'].includes(cmd);
    }
    return false;
  }

  function usesCursorNameSelect(command, fieldKey) {
    const key = String(fieldKey || '').trim();
    const cmd = String(command || '').trim().toUpperCase();
    return key === 'cursor_name' && cmd.startsWith('CURSOR_') && cmd !== 'CURSOR_NEW';
  }

  function getEventConfigFieldSpec(command, field) {
    const normalized = {
      ...(field || {}),
      label: getEventFieldLabel(field),
    };
    if (usesCursorNameSelect(command, normalized.key)) {
      return {
        ...normalized,
        type: 'select',
        options: [
          { value: '', label: 'Select cursor' },
          ...getEventCursorOptions(),
        ],
      };
    }
    if (String(command || '').trim().toUpperCase() === 'CURSOR_REPLACE' && String(normalized.key || '').trim() === 'field_name') {
      const currentLine = findEventLineById(state.eventEditor?.selectedLineId);
      const cursorName = String(currentLine?.config?.cursor_name || '').trim();
      const options = getEventCursorFieldOptions(cursorName);
      if (options.length) {
        return {
          ...normalized,
          type: 'select',
          options: [
            { value: '', label: 'Select field' },
            ...options,
          ],
        };
      }
    }
    if (!usesScreenFieldSelect(command, normalized.key)) return normalized;
    return {
      ...normalized,
      type: 'select',
      options: [
        {
          value: '',
          label: normalized.key === 'target' ? 'Select target' : 'Select field',
        },
        ...getEventSelectableFieldOptions({ includeButtons: normalized.key === 'target' }),
      ],
    };
  }

  function eventFieldPairs(line) {
    const meta = getEventCommandMeta(line?.command);
    if (!meta) return [];
    return (Array.isArray(meta.fields) ? meta.fields : [])
      .map((field) => {
        const value = eventFieldValue(line?.config, field.key);
        if (!value) return '';
        return `${getEventFieldLabel(field)}: ${value}`;
      })
      .filter(Boolean);
  }

  function buildEventLineSummary(line, { mode = 'builder' } = {}) {
    if (isEventEmptyLine(line)) return '';
    const meta = getEventCommandMeta(line.command);
    if (!meta) return String(line.command || '').trim().toUpperCase();
    const summary = eventFieldPairs(line).join(mode === 'pseudo' ? ' | ' : ' · ');
    const cmd = String(line.command || '').trim().toUpperCase();
    if (cmd === 'START') return mode === 'pseudo' ? 'START' : '';
    if (cmd === 'IF') {
      const condition = eventFieldValue(line.config, 'condition', '<condition>');
      return mode === 'pseudo' ? `IF ${condition}` : `Condition: ${condition}`;
    }
    if (cmd === 'ELSE') return mode === 'pseudo' ? 'ELSE' : '';
    if (cmd === 'ENDIF') return mode === 'pseudo' ? 'ENDIF' : '';
    if (cmd === 'WHILE') {
      const condition = eventFieldValue(line.config, 'condition', '<condition>');
      return mode === 'pseudo' ? `WHILE ${condition}` : `Condition: ${condition}`;
    }
    if (cmd === 'ENDWHILE') return mode === 'pseudo' ? 'ENDWHILE' : '';
    if (cmd === 'FOR_EACH') {
      const itemName = eventFieldValue(line.config, 'item_name', 'item');
      const source = eventFieldValue(line.config, 'source', '<list>');
      return mode === 'pseudo' ? `FOR EACH ${itemName} IN ${source}` : `Item: ${itemName} · Source: ${source}`;
    }
    if (cmd === 'ENDFOR') return mode === 'pseudo' ? 'ENDFOR' : '';
    if (cmd === 'CURSOR_SCAN') {
      const cursorName = eventFieldValue(line.config, 'cursor_name', '<cursor>');
      const rowName = eventFieldValue(line.config, 'row_name', 'ROW');
      return mode === 'pseudo' ? `CURSOR_SCAN ${cursorName} AS ${rowName}` : `Cursor: ${cursorName} · Row: ${rowName}`;
    }
    if (cmd === 'ENDCURSOR_SCAN') return mode === 'pseudo' ? 'ENDSCAN' : '';
    if (cmd === 'CURSOR_NEW') {
      const cursorName = eventFieldValue(line.config, 'cursor_name', '<cursor>');
      const cursorMode = eventFieldValue(line.config, 'cursor_mode', 'manual') || 'manual';
      if (cursorMode === 'sql') {
        const sql = getEventFieldDisplayValue(line, { key: 'sql_query' }) || '<query>';
        return mode === 'pseudo' ? `CURSOR_NEW ${cursorName} FROM SQL ${sql}` : `Cursor: ${cursorName} · SQL: ${sql}`;
      }
      const schema = getEventFieldDisplayValue(line, { key: 'cursor_fields' }) || '<fields>';
      return mode === 'pseudo' ? `CURSOR_NEW ${cursorName} (${schema})` : `Cursor: ${cursorName} · Fields: ${schema}`;
    }
    if (cmd === 'RETURN') {
      const value = eventFieldValue(line.config, 'value', '<value>');
      return mode === 'pseudo' ? `RETURN ${value}` : `Value: ${value}`;
    }
    if (cmd === 'BREAK' || cmd === 'CONTINUE') {
      return mode === 'pseudo' ? cmd : '';
    }
    if (cmd === 'DELAY') {
      const duration = eventFieldValue(line.config, 'duration_ms', '0');
      return mode === 'pseudo' ? `DELAY ${duration}ms` : `Duration: ${duration} ms`;
    }
    return mode === 'pseudo'
      ? `${getEventCommandLabel(meta).toUpperCase()}${summary ? ` ${summary}` : ''}`
      : summary;
  }

  function renderEventToolbox() {
    if (!els.eventToolbox) return;
    els.eventToolbox.innerHTML = EVENT_COMMAND_GROUPS.map((group) => `
      <section class="spv-event-group sz_panel${state.eventToolboxOpenGroup === group.id ? ' is-open' : ' is-collapsed'}">
        <button
          type="button"
          class="spv-event-group-header"
          data-event-group-toggle="${escapeHtml(group.id)}"
          aria-expanded="${state.eventToolboxOpenGroup === group.id ? 'true' : 'false'}"
        >
          <span class="spv-event-group-title">${escapeHtml(getEventGroupLabel(group.id))}</span>
          <span class="spv-event-group-chevron" aria-hidden="true">
            <i class="fa-solid fa-chevron-down"></i>
          </span>
        </button>
        <div class="spv-event-command-list"${state.eventToolboxOpenGroup === group.id ? '' : ' hidden'}>
          ${(Array.isArray(group.items) ? group.items : []).map((item) => `
            <button
              type="button"
              class="spv-event-command sz_card"
              draggable="true"
              data-event-command="${escapeHtml(item.id)}"
              title="${escapeHtml(getEventCommandLabel(item))}"
            >
              <span class="spv-event-command-label">${escapeHtml(getEventCommandLabel(item))}</span>
            </button>
          `).join('')}
        </div>
      </section>
    `).join('');
  }

  function canDragEventLine(line) {
    return !!line && !isEventEmptyLine(line) && isEventDraggableCommand(line.command);
  }

  function resolveEventDropTarget(event) {
    if (!els.eventBuilder) return null;
    const slot = event.target.closest('[data-event-slot-index]');
    if (slot) {
      return {
        slotIndex: Math.max(0, Number(slot.dataset.eventSlotIndex || 0)),
        replaceEmpty: String(slot.dataset.eventReplaceEmpty || '').trim() === '1',
        marker: slot,
        markerClass: 'is-over',
      };
    }

    const lineButton = event.target.closest('[data-event-line-id][data-event-line-index]');
    if (lineButton) {
      const rect = lineButton.getBoundingClientRect();
      const baseIndex = Math.max(0, Number(lineButton.dataset.eventLineIndex || 0));
      const placeAfter = event.clientY >= (rect.top + (rect.height / 2));
      return {
        slotIndex: baseIndex + (placeAfter ? 1 : 0),
        replaceEmpty: false,
        marker: lineButton,
        markerClass: placeAfter ? 'is-over-after' : 'is-over-before',
      };
    }

    if (!els.eventBuilder.contains(event.target)) return null;
    const lines = Array.from(els.eventBuilder.querySelectorAll('[data-event-line-id][data-event-line-index]'));
    if (!lines.length) {
      return {
        slotIndex: 0,
        replaceEmpty: false,
        marker: els.eventBuilder,
        markerClass: 'is-over',
      };
    }

    for (const line of lines) {
      const rect = line.getBoundingClientRect();
      if (event.clientY <= rect.top + (rect.height / 2)) {
        return {
          slotIndex: Math.max(0, Number(line.dataset.eventLineIndex || 0)),
          replaceEmpty: false,
          marker: line,
          markerClass: 'is-over-before',
        };
      }
    }

    const lastLine = lines[lines.length - 1];
    return {
      slotIndex: Math.max(0, Number(lastLine.dataset.eventLineIndex || 0)) + 1,
      replaceEmpty: false,
      marker: lastLine,
      markerClass: 'is-over-after',
    };
  }

  function moveEventLineToIndex(lineId, targetIndex, { replaceEmpty = false } = {}) {
    if (!state.eventEditor?.flow) return;
    const stamp = String(lineId || '').trim();
    if (!stamp) return;
    const lines = getEventEditorLines();
    const sourceIndex = lines.findIndex((line) => String(line?.id || '').trim() === stamp);
    if (sourceIndex < 0) return;
    const movingLine = lines[sourceIndex];
    if (!canDragEventLine(movingLine)) return;

    let insertAt = Math.max(0, Math.min(Number(targetIndex) || 0, lines.length));
    lines.splice(sourceIndex, 1);
    if (sourceIndex < insertAt) insertAt -= 1;

    const startIndex = lines.findIndex((line) => String(line?.command || '').trim().toUpperCase() === 'START');
    if (startIndex >= 0 && insertAt <= startIndex) {
      insertAt = startIndex + 1;
    }

    if (replaceEmpty && isEventEmptyLine(lines[insertAt])) {
      lines.splice(insertAt, 1);
    }

    insertAt = Math.max(0, Math.min(insertAt, lines.length));
    lines.splice(insertAt, 0, movingLine);
    normalizeEventDraftLines();
    state.eventEditor.selectedLineId = String(movingLine.id || '').trim();
    renderEventEditor();
  }

  function renderEventBuilder() {
    if (!els.eventBuilder) return;
    const lines = getEventEditorLines();
    const parts = ['<div class="spv-event-gap" data-event-slot-index="0"></div>'];
    lines.forEach((line, index) => {
      if (isEventEmptyLine(line)) {
        parts.push(`<div class="spv-event-gap spv-event-gap-blank" data-event-slot-index="${index}" data-event-replace-empty="1"></div>`);
      } else {
        const draggable = canDragEventLine(line);
        const summary = buildEventLineSummary(line);
        parts.push(`
          <button
            type="button"
            class="spv-event-line sz_card${String(state.eventEditor?.selectedLineId || '') === String(line.id || '') ? ' is-selected' : ''}${isEventStructuralCommand(line.command) ? ' is-structural' : ''}${draggable ? ' is-draggable' : ''}"
            data-event-line-id="${escapeHtml(line.id || '')}"
            data-event-line-index="${index}"
            draggable="${draggable ? 'true' : 'false'}"
          >
            <span class="spv-event-line-body">
              <span class="spv-event-line-title">${escapeHtml(getEventCommandLabel(getEventCommandMeta(line.command) || line.command))}</span>
              ${summary ? `<span class="spv-event-line-summary">${escapeHtml(summary)}</span>` : ''}
            </span>
          </button>
        `);
      }
      parts.push(`<div class="spv-event-gap" data-event-slot-index="${index + 1}"></div>`);
    });
    els.eventBuilder.innerHTML = parts.join('');
  }

  function renderEventConfig() {
    if (!els.eventConfig) return;
    ensureSelectedEventLine();
    const line = findEventLineById(state.eventEditor?.selectedLineId);
    if (!line) {
      els.eventConfig.innerHTML = '<div class="spv-event-note">Select a step to edit its properties.</div>';
      return;
    }
    if (isEventEmptyLine(line)) {
      els.eventConfig.innerHTML = '<div class="spv-event-note">Drop a command here to continue the flow.</div>';
      return;
    }
    const meta = getEventCommandMeta(line.command);
    const command = String(line.command || '').trim().toUpperCase();
    const fields = (Array.isArray(meta?.fields) ? meta.fields : [])
      .map((field) => getEventConfigFieldSpec(command, field))
      .filter((field) => isEventConfigFieldVisible(line, field));
    const isAutoMarker = ['ELSE', 'ENDIF', 'ENDWHILE', 'ENDFOR', 'ENDCURSOR_SCAN'].includes(command);
    if (isAutoMarker) {
      els.eventConfig.innerHTML = `
        <div class="spv-event-note">
          This marker belongs to the control structure and is managed by the editor.
        </div>
      `;
      return;
    }
    els.eventConfig.innerHTML = `
      <div class="spv-event-config-grid">
        ${fields.map((field) => {
          const value = eventFieldValue(line.config, field.key);
          const spanClass = ['textarea', 'cursor_fields'].includes(field.type) ? ' spv-event-config-span' : '';
          const options = Array.isArray(field.options) ? field.options.slice() : [];
          if (field.type === 'select' && value && !options.some((option) => String(option.value || '') === value)) {
            options.unshift({ value, label: value });
          }
          return `
            <div class="sz_field${spanClass}">
              <label class="sz_label" for="spvEventConfig_${escapeHtml(field.key)}">${escapeHtml(field.label)}</label>
              ${field.type === 'textarea'
                ? `<textarea id="spvEventConfig_${escapeHtml(field.key)}" class="sz_textarea" rows="${escapeHtml(String(field.rows || 3))}" data-event-config-key="${escapeHtml(field.key)}" placeholder="${escapeHtml(field.placeholder || '')}">${escapeHtml(value)}</textarea>`
                : field.type === 'number'
                ? `<input id="spvEventConfig_${escapeHtml(field.key)}" type="number" class="sz_input" data-event-config-key="${escapeHtml(field.key)}" value="${escapeHtml(value)}"${field.step ? ` step="${escapeHtml(field.step)}"` : ''}${field.min ? ` min="${escapeHtml(field.min)}"` : ''} placeholder="${escapeHtml(field.placeholder || '')}">`
                : field.type === 'select'
                ? `<select id="spvEventConfig_${escapeHtml(field.key)}" class="sz_select" data-event-config-key="${escapeHtml(field.key)}">
                    ${options.map((option) => `
                      <option value="${escapeHtml(option.value)}" ${String(option.value || '') === value ? 'selected' : ''}>${escapeHtml(option.label)}</option>
                    `).join('')}
                  </select>`
                : field.type === 'cursor_fields'
                ? renderEventCursorFieldsMarkup(field, line)
                : `<input id="spvEventConfig_${escapeHtml(field.key)}" type="text" class="sz_input" data-event-config-key="${escapeHtml(field.key)}" value="${escapeHtml(value)}" placeholder="${escapeHtml(field.placeholder || '')}">`}
            </div>
          `;
        }).join('')}
      </div>
      <div class="spv-event-config-actions">
        <button type="button" class="sz_button sz_button_ghost" data-event-action="remove-step">
          <i class="fa-solid fa-trash"></i>
          <span>${isEventBlockOpenCommand(command) ? 'Remove block' : 'Remove step'}</span>
        </button>
      </div>
    `;
  }

  function renderEventCode() {
    if (!els.eventCode) return;
    const flow = state.eventEditor?.flow || createDefaultEventFlow();
    els.eventCode.textContent = buildEventPseudoCode(flow);
  }

  function renderEventLegacyState() {
    if (!els.eventEditorLegacy) return;
    const legacyScript = String(state.eventEditor?.legacyScript || '').trim();
    if (!legacyScript) {
      els.eventEditorLegacy.classList.add('sz_hidden');
      els.eventEditorLegacy.textContent = '';
      return;
    }
    els.eventEditorLegacy.classList.remove('sz_hidden');
    els.eventEditorLegacy.textContent = 'Existe um script JS legado neste evento. O editor visual grava o novo fluxo em PROPRIEDADES.events, mas nao converte automaticamente esse JS.';
  }

  function renderEventEditor() {
    if (!state.eventEditor) return;
    renderEventToolbox();
    renderEventLegacyState();
    renderEventBuilder();
    renderEventConfig();
    renderEventCode();
  }

  function openFieldEventEditor(fieldStamp = state.selectedFieldStamp, eventName = 'click') {
    const field = findFieldByStamp(fieldStamp);
    if (!field) {
      setStatus('Seleciona um objeto antes de editar eventos.', 'danger');
      showToast('Seleciona um objeto antes de editar eventos.', 'error');
      return;
    }
    const rawFlow = getFieldEventDefinition(field, eventName);
    const normalized = rawFlow ? normalizeEventFlow(cloneJson(rawFlow, {})) : createDefaultEventFlow();
    normalized.pseudo_code = buildEventPseudoCode(normalized);
    state.eventEditor = {
      scope: 'field',
      targetStamp: getFieldStamp(field),
      targetLabel: fieldLabel(field),
      eventName: String(eventName || 'click').trim().toLowerCase(),
      flow: normalized,
      selectedLineId: String((normalized.lines.find((line) => !isEventEmptyLine(line)) || {}).id || '').trim(),
      legacyScript: getFieldClickAction(field),
    };
    if (els.eventEditorTitle) {
      els.eventEditorTitle.textContent = `Editor de evento: ${String(eventName || 'click').trim()}`;
    }
    if (els.eventEditorContext) {
      els.eventEditorContext.textContent = `Objeto ${fieldLabel(field)} associado ao menu selecionado.`;
    }
    renderEventEditor();
    const modal = getEventEditorModalInstance();
    if (modal) {
      modal.show();
      return;
    }
    showToast('Bootstrap modal indisponivel nesta pagina.', 'error');
  }

  function openScreenEventEditor(eventName = 'init') {
    const menu = getScreenMenu();
    if (!String(menu.MENUSTAMP || '').trim()) {
      setStatus('Seleciona um ecrã antes de editar eventos.', 'danger');
      showToast('Seleciona um ecrã antes de editar eventos.', 'error');
      return;
    }
    const rawFlow = getMenuEventDefinition(menu, eventName);
    const normalized = rawFlow ? normalizeEventFlow(cloneJson(rawFlow, {})) : createDefaultEventFlow();
    normalized.pseudo_code = buildEventPseudoCode(normalized);
    state.eventEditor = {
      scope: 'screen',
      targetStamp: String(menu.MENUSTAMP || '').trim(),
      targetLabel: String(menu.NOME || menu.TABELA || 'Screen').trim() || 'Screen',
      eventName: String(eventName || 'init').trim().toLowerCase(),
      flow: normalized,
      selectedLineId: String((normalized.lines.find((line) => !isEventEmptyLine(line)) || {}).id || '').trim(),
      legacyScript: '',
    };
    if (els.eventEditorTitle) {
      els.eventEditorTitle.textContent = `Editor de evento: ${String(eventName || 'init').trim()}`;
    }
    if (els.eventEditorContext) {
      els.eventEditorContext.textContent = `Ecrã ${state.eventEditor.targetLabel} associado ao menu selecionado.`;
    }
    renderEventEditor();
    const modal = getEventEditorModalInstance();
    if (modal) {
      modal.show();
      return;
    }
    showToast('Bootstrap modal indisponivel nesta pagina.', 'error');
  }

  function closeEventEditor() {
    const modal = getEventEditorModalInstance();
    modal?.hide?.();
  }

  function resetEventEditorState() {
    state.eventEditor = null;
    state.eventDrag = null;
    clearEventDropMarkers();
    if (els.eventConfig) els.eventConfig.innerHTML = '';
    if (els.eventBuilder) els.eventBuilder.innerHTML = '';
    if (els.eventCode) els.eventCode.textContent = '';
    if (els.eventEditorLegacy) {
      els.eventEditorLegacy.classList.add('sz_hidden');
      els.eventEditorLegacy.textContent = '';
    }
  }

  function updateSelectedEventConfig(key, nextValue, { rerenderConfig = true } = {}) {
    const line = findEventLineById(state.eventEditor?.selectedLineId);
    if (!line || isEventEmptyLine(line)) return;
    if (!line.config || typeof line.config !== 'object') {
      line.config = {};
    }
    const value = String(nextValue ?? '').trim();
    if (value) {
      line.config[key] = value;
    } else {
      delete line.config[key];
    }
    renderEventBuilder();
    if (rerenderConfig) renderEventConfig();
    renderEventCode();
  }

  async function clearEventEditorFlow() {
    if (!state.eventEditor?.flow) return;
    const confirmed = await confirmDelete('Pretende limpar o fluxo visual deste evento?');
    if (!confirmed) return;
    state.eventEditor.flow = createDefaultEventFlow();
    state.eventEditor.selectedLineId = String(state.eventEditor.flow.lines[0]?.id || '').trim();
    renderEventEditor();
  }

  function saveEventEditor() {
    const editor = state.eventEditor;
    const field = getEventEditorField();
    const menu = getEventEditorMenu();
    if (!editor || (editor.scope === 'field' && !field) || (editor.scope === 'screen' && !menu)) return;
    const normalized = normalizeEventFlow(editor.flow);
    normalized.pseudo_code = buildEventPseudoCode(normalized);
    const nextFlow = {
      version: 1,
      source: 'visual-editor',
      lines: normalized.lines.map((line) => (
        isEventEmptyLine(line)
          ? { kind: 'empty' }
          : (() => {
            const nextConfig = cloneJson(line.config, {}) || {};
            if (Array.isArray(nextConfig.cursor_fields)) {
              nextConfig.cursor_fields = nextConfig.cursor_fields
                .map(normalizeEventCursorField)
                .filter((entry) => entry.name);
              if (!nextConfig.cursor_fields.length) {
                delete nextConfig.cursor_fields;
              }
            }
            return {
              kind: 'command',
              command: String(line.command || '').trim().toUpperCase(),
              config: nextConfig,
            };
          })()
      )),
      pseudo_code: normalized.pseudo_code,
    };
    if (editor.scope === 'field') {
      if (!field.PROPRIEDADES || typeof field.PROPRIEDADES !== 'object') {
        field.PROPRIEDADES = {};
      }
      const events = getFieldEvents(field);
      const nextEvents = { ...events };
      if (countMeaningfulEventCommands(normalized) > 0) {
        nextEvents[editor.eventName] = nextFlow;
        field.PROPRIEDADES.events = nextEvents;
      } else {
        delete nextEvents[editor.eventName];
        if (Object.keys(nextEvents).length) {
          field.PROPRIEDADES.events = nextEvents;
        } else {
          delete field.PROPRIEDADES.events;
        }
      }
    } else if (editor.scope === 'screen') {
      const nextEvents = {
        ...getMenuEvents(menu),
      };
      if (countMeaningfulEventCommands(normalized) > 0) {
        nextEvents[editor.eventName] = nextFlow;
      } else {
        delete nextEvents[editor.eventName];
      }
      menu.EVENTS = nextEvents;
    } else {
      return;
    }
    closeEventEditor();
    renderSidebarList();
    renderPreview();
    renderProperties();
    setStatus(`Evento ${editor.eventName} atualizado localmente. Nao gravado.`);
  }

  function renderPreview() {
    const detail = state.detail || {};
    const menu = normalizeMenuRow(detail.menu || {});
    ensureSelectedField();

    if (!menu.MENUSTAMP) {
      els.previewEmpty?.classList.remove('sz_hidden');
      els.previewStage?.classList.add('sz_hidden');
      if (els.previewScale) els.previewScale.innerHTML = '';
      return;
    }

    if (isListLayoutMode()) {
      if (isMobileMode()) {
        normalizeListMobileLayout();
        const grouped = groupPreviewFields(getDetailFields());
        const displayGroups = grouped.slice();
        if (state.drag?.active) {
          const nextRowId = grouped.length
            ? Math.max(...grouped.map(([rowId]) => Number(rowId) || 0)) + 1
            : 1;
          displayGroups.push([nextRowId, []]);
        }

        const rowsHtml = displayGroups.map(([rowId, rowFields]) => {
          const rowDrag = getRowDragState(rowId);
          const gapDrag = getGapDragState(rowId);
          const draggedStamp = String(state.drag?.fieldStamp || '').trim();
          const dragSize = getDragSize(state.drag);
          const sourceRowId = Number(state.drag?.sourceRowId || -1);
          const renderFields = rowDrag && rowDrag.valid && String(state.drag?.sourceKind || 'layout') === 'layout' && sourceRowId === Number(rowId)
            ? rowFields.filter((field) => getFieldStamp(field) !== draggedStamp)
            : rowFields.slice();

          const items = [];
          renderFields.forEach((field, index) => {
            if (rowDrag && rowDrag.valid && Number(rowDrag.overIndex) === index) {
              items.push({ type: 'placeholder', size: dragSize });
            }
            items.push({ type: 'field', field });
          });
          if (rowDrag && rowDrag.valid && Number(rowDrag.overIndex) >= renderFields.length) {
            items.push({ type: 'placeholder', size: dragSize });
          }

          const rowUnits = items.reduce((acc, item) => {
            if (item.type === 'placeholder') return acc + Number(item.size || 5);
            return acc + getFieldSize(item.field);
          }, 0);
          const layoutUnits = state.useExactWidths ? getPreviewGridUnits() : Math.max(1, rowUnits);
          const rowClasses = ['spv-preview-row', 'spv-preview-row-card'];
          if (rowDrag?.valid) rowClasses.push('is-drop-target');
          if (rowDrag && !rowDrag.valid) rowClasses.push('is-drop-invalid');
          if (!rowFields.length) rowClasses.push('is-new-row');

          const colsHtml = items.map((item) => {
            if (item.type === 'placeholder') {
              return buildDropPlaceholder(Number(item.size || 5));
            }
            const field = item.field;
            const size = getFieldSize(field);
            const fieldStamp = getFieldStamp(field);
            const fieldClasses = ['spv-preview-field', 'spv-preview-field-list-mobile'];
            if (state.selectedScope === 'field' && fieldStamp && fieldStamp === state.selectedFieldStamp) fieldClasses.push('is-selected');
            if (state.drag?.active && String(state.drag?.sourceKind || 'layout') === 'layout' && fieldStamp && fieldStamp === draggedStamp) fieldClasses.push('is-drag-source');
            return `
              <div class="spv-preview-col" data-campostamp="${escapeHtml(fieldStamp)}" style="grid-column: span ${size};">
                <div class="${fieldClasses.join(' ')}" data-campostamp="${escapeHtml(fieldStamp)}">
                  ${buildListMobilePreviewControl(field)}
                </div>
              </div>
            `;
          }).join('');

          const rowHint = !rowFields.length && !items.length
            ? '<div class="spv-row-hint">Nova linha do card</div>'
            : '';
          const invalidOverlay = rowDrag && !rowDrag.valid
            ? `<div class="spv-drop-placeholder spv-drop-placeholder-inline is-invalid"><span>Sem espaco nesta linha</span></div>`
            : '';
          const insertGap = gapDrag ? `
            <div class="spv-preview-insert-gap ${gapDrag?.valid ? 'is-drop-target' : ''}" data-before-row-id="${Number(rowId)}">
              <div class="spv-preview-insert-gap-inner">${gapDrag?.valid ? 'Largar aqui' : ''}</div>
            </div>
          ` : '';
          return `
            ${insertGap}
            <div class="${rowClasses.join(' ')}" data-row-id="${Number(rowId)}" style="grid-template-columns: repeat(${layoutUnits}, minmax(0, 1fr));">
              ${colsHtml}
              ${rowHint}
              ${invalidOverlay}
            </div>
          `;
        }).join('');

        if (els.previewScale) {
          els.previewScale.innerHTML = buildPreviewFrame(
            rowsHtml || `
              <div class="spv-list-preview-mobile-placeholder">
                <div class="sz_h4">Lista mobile</div>
                <div class="sz_text_muted">Arrasta campos para definir as linhas do card.</div>
              </div>
            `,
            {
              mobile: true,
              panelClass: 'spv-list-mobile-card',
            },
          );
        }
        els.previewEmpty?.classList.add('sz_hidden');
        els.previewStage?.classList.remove('sz_hidden');
        syncPreviewScaleHeight();
        return;
        if (els.previewScale) {
          els.previewScale.innerHTML = `
            <div class="spv-preview-screen">
              <div class="spv-preview-body">
                <div class="sz_card spv-list-preview-mobile-placeholder">
                  <div class="sz_h4">Lista mobile</div>
                  <div class="sz_text_muted">Ainda não está definida neste editor.</div>
                </div>
              </div>
            </div>
          `;
        }
        els.previewEmpty?.classList.add('sz_hidden');
        els.previewStage?.classList.remove('sz_hidden');
        syncPreviewScaleHeight();
        return;
      }

      const rowFields = getVisibleListFields();

      const rowDrag = state.drag?.active && Number(state.drag?.overRowId || 0) === 1
        ? state.drag
        : null;
      const draggedStamp = String(state.drag?.fieldStamp || '').trim();
      const dragSize = getDragSize(state.drag);
      const renderFields = rowDrag && String(state.drag?.sourceKind || 'layout') === 'layout'
        ? rowFields.filter((field) => getFieldStamp(field) !== draggedStamp)
        : rowFields.slice();
      const items = [];
      renderFields.forEach((field, index) => {
        if (rowDrag && rowDrag.valid && Number(rowDrag.overIndex) === index) {
          items.push({ type: 'placeholder', size: dragSize });
        }
        items.push({ type: 'field', field });
      });
      if (rowDrag && rowDrag.valid && Number(rowDrag.overIndex) >= renderFields.length) {
        items.push({ type: 'placeholder', size: dragSize });
      }

      if (!items.length) {
        items.push({ type: 'placeholder', size: 20 });
      }

      const rowUnits = items.reduce((acc, item) => (
        acc + (item.type === 'placeholder' ? Number(item.size || 5) : getFieldSize(item.field))
      ), 0);
      const layoutUnits = state.useExactWidths ? getPreviewGridUnits() : Math.max(1, rowUnits);
      const colsHtml = items.map((item) => {
        if (item.type === 'placeholder') {
          return buildDropPlaceholder(Number(item.size || 5), { invalid: false });
        }
        const field = item.field;
        const size = getFieldSize(field);
        const fieldStamp = getFieldStamp(field);
        const fieldClasses = ['spv-preview-field', 'spv-preview-field-list'];
        if (state.selectedScope === 'field' && fieldStamp && fieldStamp === state.selectedFieldStamp) fieldClasses.push('is-selected');
        if (state.drag?.active && String(state.drag?.sourceKind || 'layout') === 'layout' && fieldStamp && fieldStamp === draggedStamp) fieldClasses.push('is-drag-source');
        return `
          <div class="spv-preview-col" data-campostamp="${escapeHtml(fieldStamp)}" style="grid-column: span ${size};">
            <div class="${fieldClasses.join(' ')}" data-campostamp="${escapeHtml(fieldStamp)}">
              ${buildListPreviewControl(field)}
            </div>
          </div>
        `;
      }).join('');

      const invalidOverlay = rowDrag && !rowDrag.valid
        ? `<div class="spv-drop-placeholder spv-drop-placeholder-inline is-invalid"><span>Sem espaço suficiente</span></div>`
        : '';
      const rowHint = !rowFields.length
        ? '<div class="spv-row-hint">Arrasta campos para começar a lista</div>'
        : '';

      if (els.previewScale) {
        els.previewScale.innerHTML = buildPreviewFrame(`
          <div class="spv-preview-row spv-preview-row-list${rowDrag?.valid ? ' is-drop-target' : ''}${rowDrag && !rowDrag.valid ? ' is-drop-invalid' : ''}" data-row-id="1" style="grid-template-columns: repeat(${layoutUnits}, minmax(0, 1fr));">
            ${colsHtml}
            ${rowHint}
            ${invalidOverlay}
          </div>
        `);
      }
      els.previewEmpty?.classList.add('sz_hidden');
      els.previewStage?.classList.remove('sz_hidden');
      syncPreviewScaleHeight();
      return;
    }

    const fields = getLayoutItems().map(normalizeCampoRow);
    const grouped = groupPreviewFields(fields);

    if (!grouped.length) {
      els.previewEmpty?.classList.remove('sz_hidden');
      els.previewStage?.classList.add('sz_hidden');
      if (els.previewScale) els.previewScale.innerHTML = '';
      return;
    }

    const displayGroups = grouped.slice();
    if (state.drag?.active) {
      const nextRowId = grouped.length
        ? Math.max(...grouped.map(([rowId]) => Number(rowId) || 0)) + 1
        : 1;
      displayGroups.push([nextRowId, []]);
    }

    const rowsHtml = displayGroups.map(([rowId, rowFields]) => {
      const rowDrag = getRowDragState(rowId);
      const gapDrag = getGapDragState(rowId);
      const draggedStamp = String(state.drag?.fieldStamp || '').trim();
      const dragSize = getDragSize(state.drag);
      const sourceRowId = Number(state.drag?.sourceRowId || -1);
      const renderFields = rowDrag && rowDrag.valid && String(state.drag?.sourceKind || 'layout') === 'layout' && sourceRowId === Number(rowId)
        ? rowFields.filter((field) => getFieldStamp(field) !== draggedStamp)
        : rowFields.slice();

      const items = [];
      renderFields.forEach((field, index) => {
        if (rowDrag && rowDrag.valid && Number(rowDrag.overIndex) === index) {
          items.push({
            type: 'placeholder',
            size: dragSize,
          });
        }
        items.push({
          type: 'field',
          field,
        });
      });
      if (rowDrag && rowDrag.valid && Number(rowDrag.overIndex) >= renderFields.length) {
        items.push({
          type: 'placeholder',
          size: dragSize,
        });
      }

      const rowUnits = items.reduce((acc, item) => {
        if (item.type === 'placeholder') return acc + Number(item.size || 5);
        return acc + getFieldSize(item.field);
      }, 0);
      const layoutUnits = state.useExactWidths ? getPreviewGridUnits() : Math.max(1, rowUnits);
      const rowClasses = ['spv-preview-row'];
      if (rowDrag?.valid) rowClasses.push('is-drop-target');
      if (rowDrag && !rowDrag.valid) rowClasses.push('is-drop-invalid');
      if (!rowFields.length) rowClasses.push('is-new-row');

      const colsHtml = items.map((item) => {
        if (item.type === 'placeholder') {
          return buildDropPlaceholder(Number(item.size || 5));
        }
        const field = item.field;
        const size = getFieldSize(field);
        const fieldStamp = getFieldStamp(field);
        const fieldClasses = ['spv-preview-field'];
        if (state.selectedScope === 'field' && fieldStamp && fieldStamp === state.selectedFieldStamp) fieldClasses.push('is-selected');
        if (state.drag?.active && String(state.drag?.sourceKind || 'layout') === 'layout' && fieldStamp && fieldStamp === draggedStamp) fieldClasses.push('is-drag-source');
        return `
          <div class="spv-preview-col" data-campostamp="${escapeHtml(fieldStamp)}" style="grid-column: span ${size};">
            <div class="${fieldClasses.join(' ')}" data-campostamp="${escapeHtml(fieldStamp)}">
              ${buildPreviewControl(field)}
            </div>
          </div>
        `;
      }).join('');
      const rowHint = !rowFields.length && !items.length
        ? '<div class="spv-row-hint">Nova linha</div>'
        : '';
      const invalidOverlay = rowDrag && !rowDrag.valid
        ? `<div class="spv-drop-placeholder spv-drop-placeholder-inline is-invalid"><span>Sem espaço nesta linha</span></div>`
        : '';
      const insertGap = gapDrag ? `
        <div class="spv-preview-insert-gap ${gapDrag?.valid ? 'is-drop-target' : ''}" data-before-row-id="${Number(rowId)}">
          <div class="spv-preview-insert-gap-inner">${gapDrag?.valid ? 'Largar aqui' : ''}</div>
        </div>
      ` : '';
      return `
        ${insertGap}
        <div class="${rowClasses.join(' ')}" data-row-id="${Number(rowId)}" style="grid-template-columns: repeat(${layoutUnits}, minmax(0, 1fr));">
          ${colsHtml}
          ${rowHint}
          ${invalidOverlay}
        </div>
      `;
    }).join('');

    if (els.previewScale) {
      els.previewScale.innerHTML = buildPreviewFrame(rowsHtml, {
        mobile: isMobileMode(),
      });
    }
    els.previewEmpty?.classList.add('sz_hidden');
    els.previewStage?.classList.remove('sz_hidden');
    syncPreviewScaleHeight();
  }

  function renderAll() {
    renderScreenOptions();
    renderLayoutModeToggle();
    renderViewportModeToggle();
    renderWidthModeToggle();
    renderSidebarList();
    renderPreview();
    renderProperties();
    renderActionState();
  }

  function findFieldByStamp(fieldStamp) {
    const stamp = String(fieldStamp || '').trim();
    if (!stamp) return null;
    return getLayoutItems().find((field) => getFieldStamp(field) === stamp) || null;
  }

  function findKnownFieldByStamp(fieldStamp) {
    const stamp = String(fieldStamp || '').trim();
    if (!stamp) return null;
    return getAllScreenItems().find((field) => getFieldStamp(field) === stamp) || null;
  }

  function getRowFieldsForStamp(fieldStamp) {
    const target = findFieldByStamp(fieldStamp);
    if (!target) return [];
    const rowKey = fieldRowGroup(target);
    return getLayoutItems()
      .map(normalizeCampoRow)
      .filter((field) => isVisibleField(field) && fieldRowGroup(field) === rowKey);
  }

  function clampFieldSize(fieldStamp, proposedSize) {
    const target = findFieldByStamp(fieldStamp);
    if (!target) return 5;
    const sameRow = getRowFieldsForStamp(fieldStamp);
    const otherTotal = sameRow.reduce((acc, field) => {
      const same = getFieldStamp(field) === String(fieldStamp || '').trim();
      return acc + (same ? 0 : getFieldSize(field));
    }, 0);
    const maxSize = Math.max(5, getPreviewGridUnits() - otherTotal);
    const maxSnap = Math.max(5, Math.floor(maxSize / 5) * 5);
    const snapped = Math.round(Number(proposedSize || 1) / 5) * 5;
    return Math.max(5, Math.min(maxSnap, snapped || 5));
  }

  function updateFieldSize(fieldStamp, nextSize) {
    const target = findFieldByStamp(fieldStamp);
    if (!target) return false;
    const normalizedSize = clampFieldSize(fieldStamp, nextSize);
    const widthKey = getActiveWidthField();
    if (Number(target[widthKey] || 1) === normalizedSize) return false;
    target[widthKey] = normalizedSize;
    return true;
  }

  function setDragTarget(nextTarget = {}) {
    if (!state.drag) return;
    const current = state.drag;
    const nextRowId = Number.isFinite(Number(nextTarget.rowId)) ? Number(nextTarget.rowId) : null;
    const nextIndex = Number.isFinite(Number(nextTarget.index)) ? Number(nextTarget.index) : null;
    const nextMode = String(nextTarget.mode || 'row');
    const nextValid = !!nextTarget.valid;
    const changed = current.overRowId !== nextRowId
      || current.overIndex !== nextIndex
      || String(current.overMode || 'row') !== nextMode
      || current.valid !== nextValid;
    if (!changed) return;
    state.drag.overRowId = nextRowId;
    state.drag.overIndex = nextIndex;
    state.drag.overMode = nextMode;
    state.drag.valid = nextValid;
    renderPreview();
  }

  function updateDragTargetFromPoint(clientX, clientY) {
    if (!state.drag?.active) return;
    if (isListLayoutMode()) {
      const hovered = document.elementFromPoint(clientX, clientY);
      const rowElement = hovered?.closest?.('.spv-preview-row[data-row-id]');
      if (!rowElement) {
        setDragTarget();
        return;
      }
      const rowId = Number(rowElement.dataset.rowId || 1);
      const excludeStamp = String(state.drag.sourceKind || 'layout') === 'layout' ? state.drag.fieldStamp : '';
      const rowFields = getVisibleListFields({ excludeStamp });
      let index = rowFields.length;
      const rowColumns = Array.from(rowElement.querySelectorAll('.spv-preview-col[data-campostamp]'))
        .filter((col) => String(col.dataset.campostamp || '').trim() !== String(excludeStamp || '').trim());
      if (rowColumns.length) {
        for (let pointer = 0; pointer < rowColumns.length; pointer += 1) {
          const column = rowColumns[pointer];
          const stamp = String(column.dataset.campostamp || '').trim();
          const rect = column.getBoundingClientRect();
          const centerX = rect.left + (rect.width / 2);
          if (clientX < centerX) {
            const position = rowFields.findIndex((field) => getFieldStamp(field) === stamp);
            index = position >= 0 ? position : pointer;
            break;
          }
        }
      }
      setDragTarget({
        rowId,
        index,
        mode: 'row',
        valid: canFieldFitRow(state.drag.fieldStamp, rowId, { sourceKind: state.drag.sourceKind }),
      });
      return;
    }
    const hovered = document.elementFromPoint(clientX, clientY);
    const gapElement = hovered?.closest?.('.spv-preview-insert-gap[data-before-row-id]');
    if (gapElement) {
      const rowId = Number(gapElement.dataset.beforeRowId || 0);
      setDragTarget({
        rowId,
        index: 0,
        mode: 'gap',
        valid: true,
      });
      return;
    }
    const rowElement = hovered?.closest?.('.spv-preview-row[data-row-id]');
    if (!rowElement) {
      setDragTarget();
      return;
    }
    const rowId = Number(rowElement.dataset.rowId || 0);
    const isNewRow = rowElement.classList.contains('is-new-row');
    const maxExistingRow = getVisibleLayoutFields().reduce((max, field) => Math.max(max, getFieldRowId(field)), 0);
    const rect = rowElement.getBoundingClientRect();
    const edgeThreshold = Math.max(10, Math.min(20, rect.height * 0.28));

    if (!isNewRow && clientY <= (rect.top + edgeThreshold)) {
      setDragTarget({
        rowId,
        index: 0,
        mode: 'gap',
        valid: true,
      });
      return;
    }

    if (!isNewRow && rowId < maxExistingRow && clientY >= (rect.bottom - edgeThreshold)) {
      setDragTarget({
        rowId: rowId + 1,
        index: 0,
        mode: 'gap',
        valid: true,
      });
      return;
    }

    const excludeStamp = Number(state.drag.sourceRowId) === rowId ? state.drag.fieldStamp : '';
    const rowFields = getRowFields(rowId, { excludeStamp });
    let index = rowFields.length;

    const rowColumns = Array.from(rowElement.querySelectorAll('.spv-preview-col[data-campostamp]'))
      .filter((col) => String(col.dataset.campostamp || '').trim() !== String(excludeStamp || '').trim());

    if (rowColumns.length) {
      index = rowFields.length;
      for (let pointer = 0; pointer < rowColumns.length; pointer += 1) {
        const column = rowColumns[pointer];
        const stamp = String(column.dataset.campostamp || '').trim();
        const rect = column.getBoundingClientRect();
        const centerX = rect.left + (rect.width / 2);
        if (clientX < centerX) {
          const position = rowFields.findIndex((field) => getFieldStamp(field) === stamp);
          index = position >= 0 ? position : pointer;
          break;
        }
      }
    }
    setDragTarget({
      rowId,
      index,
      mode: 'row',
      valid: canFieldFitRow(state.drag.fieldStamp, rowId, { sourceKind: state.drag.sourceKind }),
    });
  }

  function beginFieldDrag(fieldStamp, event, { sourceKind = 'layout', templateId = '' } = {}) {
    const target = sourceKind === 'layout' ? findFieldByStamp(fieldStamp) : null;
    if (sourceKind === 'layout' && !target) return;
    state.drag = {
      fieldStamp,
      sourceRowId: sourceKind === 'layout' ? getFieldRowId(target) : -1,
      startX: Number(event.clientX || 0),
      startY: Number(event.clientY || 0),
      sourceKind,
      templateId: String(templateId || '').trim(),
      active: false,
      overRowId: null,
      overIndex: null,
      overMode: 'row',
      valid: false,
    };
    document.addEventListener('mousemove', handleFieldDragMove);
    document.addEventListener('mouseup', handleFieldDragEnd);
  }

  function handleFieldDragMove(event) {
    if (!state.drag) return;
    const deltaX = Math.abs(Number(event.clientX || 0) - Number(state.drag.startX || 0));
    const deltaY = Math.abs(Number(event.clientY || 0) - Number(state.drag.startY || 0));
    if (!state.drag.active) {
      if (deltaX < 4 && deltaY < 4) return;
      state.drag.active = true;
      document.body.classList.add('spv-dragging');
      selectField(state.drag.fieldStamp, { render: false });
    }
    updateDragTargetFromPoint(Number(event.clientX || 0), Number(event.clientY || 0));
    event.preventDefault();
  }

  function clearFieldDrag() {
    document.removeEventListener('mousemove', handleFieldDragMove);
    document.removeEventListener('mouseup', handleFieldDragEnd);
    document.body.classList.remove('spv-dragging');
    state.drag = null;
  }

  function handleFieldDragEnd() {
    if (!state.drag) return;
    const drag = { ...state.drag };
    clearFieldDrag();
    if (drag.active) {
      state.suppressPreviewClickUntil = Date.now() + 180;
    }
    if (!drag.active) {
      selectField(drag.fieldStamp);
      return;
    }
    if (!drag.valid || !Number.isFinite(Number(drag.overRowId))) {
      renderAll();
      setStatus('Sem espaço suficiente na linha de destino. Alteração local não aplicada.');
      return;
    }
    if (isListLayoutMode() && !isMobileMode()) {
      const movedList = moveFieldToList(drag.fieldStamp, drag.overIndex);
      renderAll();
      if (movedList) {
        const target = findFieldByStamp(drag.fieldStamp);
        if (target) {
          selectField(getFieldStamp(target), { render: false });
          renderAll();
          setStatus(`Ajuste local aplicado: ${fieldLabel(target)} movido para a lista. Nao gravado.`);
          return;
        }
      }
      setStatus('Ajuste local nao aplicado.');
      return;
    }
    const moved = String(drag.overMode || 'row') === 'gap'
      ? insertFieldAsNewRow(drag.fieldStamp, drag.overRowId, {
        sourceKind: drag.sourceKind,
        templateId: drag.templateId,
      })
      : (String(drag.sourceKind || 'layout') === 'catalog'
        ? insertCustomObjectToRow(drag.templateId, drag.overRowId, drag.overIndex)
        : moveFieldToRow(drag.fieldStamp, drag.overRowId, drag.overIndex));
    renderAll();
    if (moved) {
      const target = String(drag.sourceKind || 'layout') === 'catalog'
        ? moved
        : findFieldByStamp(drag.fieldStamp);
      if (target) {
        selectField(getFieldStamp(target), { render: false });
        renderAll();
        setStatus(`Ajuste local aplicado: ${fieldLabel(target)} movido para a linha ${getFieldRowId(target)}. Não gravado.`);
        return;
      }
      setStatus('Ajuste local aplicado. Não gravado.');
      return;
    }
    setStatus('Ajuste local não aplicado.');
  }

  function selectField(fieldStamp, { render = true } = {}) {
    const target = findKnownFieldByStamp(fieldStamp);
    state.selectedFieldStamp = target ? getFieldStamp(target) : '';
    state.selectedScope = target ? 'field' : getDefaultSelectionScope();
    if (render) renderAll();
  }

  function setLayoutMode(mode) {
    const nextMode = String(mode || 'form').trim().toLowerCase() === 'list' ? 'list' : 'form';
    if (state.layoutMode === nextMode) return;
    state.layoutMode = nextMode;
    if (nextMode === 'list') {
      state.sidebarMode = 'fields';
      if (isMobileMode()) {
        normalizeListMobileLayout();
      } else {
        normalizeListDesktopLayout();
      }
    }
    syncWidthModeFromMenu(getScreenMenu());
    state.selectedFieldStamp = getDefaultFieldStamp();
    state.selectedScope = getDefaultSelectionScope();
    renderAll();
    setStatus(nextMode === 'list'
      ? 'Modo lista. O desktop configura colunas e o mobile configura cards do dynamic_list.'
      : 'Modo form. O preview usa o layout do dynamic_form.');
  }

  function setWidthMode(useExact) {
    state.useExactWidths = !!useExact;
    if (state.detail?.menu) {
      if (isListLayoutMode()) {
        state.detail.menu.LARGURAS_EXATAS_LISTA = state.useExactWidths ? 1 : 0;
      } else {
        state.detail.menu.LARGURAS_EXATAS = state.useExactWidths ? 1 : 0;
      }
    }
    renderAll();
    setStatus(state.useExactWidths
      ? `Modo ${isListLayoutMode() ? 'lista' : 'form'}. Larguras exatas ativas.`
      : `Modo ${isListLayoutMode() ? 'lista' : 'form'}. Larguras proporcionais ativas.`);
  }

  function setViewportMode(mode) {
    const nextMode = String(mode || 'desktop').trim().toLowerCase() === 'mobile' ? 'mobile' : 'desktop';
    if (state.viewportMode === nextMode) return;
    state.viewportMode = nextMode;
    renderAll();
    if (isListLayoutMode()) {
      setStatus(nextMode === 'mobile'
        ? 'Modo lista mobile. Configura o card usado no dynamic_list.'
        : 'Modo lista desktop. Configura ordem e largura das colunas.');
      return;
    }
    setStatus(nextMode === 'mobile'
      ? 'Modo mobile. O preview usa ORDEM_MOBILE e TAM_MOBILE.'
      : 'Modo desktop. O preview usa ORDEM e TAM.');
  }

  function finishResize(commitMessage = '') {
    state.resize = null;
    document.body.classList.remove('spv-resizing');
    renderAll();
    if (commitMessage) setStatus(commitMessage);
  }

  function handleResizeMove(event) {
    if (!state.resize) return;
    const deltaX = Number(event.clientX || 0) - state.resize.startX;
    const deltaPercent = (deltaX / state.resize.rowWidth) * 100;
    const nextSize = state.resize.startSize + deltaPercent;
    const changed = updateFieldSize(state.resize.fieldStamp, nextSize);
    if (changed) {
      renderSidebarList();
      renderPreview();
      renderProperties();
      const target = findFieldByStamp(state.resize.fieldStamp);
      if (target) {
        setStatus(`Ajuste local: ${fieldLabel(target)} = ${Number(target?.[getActiveWidthField()] || 1)}% da largura. N?o gravado.`);
      }
    }
  }

  function handleResizeEnd() {
    if (!state.resize) return;
    const target = findFieldByStamp(state.resize.fieldStamp);
    const message = target
      ? `Ajuste local aplicado: ${fieldLabel(target)} = ${Number(target?.[getActiveWidthField()] || 1)}%. Não gravado.`
      : 'Ajuste local aplicado. Não gravado.';
    document.removeEventListener('mousemove', handleResizeMove);
    document.removeEventListener('mouseup', handleResizeEnd);
    finishResize(message);
  }

  function beginResize(handle, event) {
    const fieldStamp = String(handle?.dataset?.campostamp || '').trim();
    if (!fieldStamp) return;
    const row = handle.closest('.spv-preview-row');
    const target = findFieldByStamp(fieldStamp);
    if (!row || !target) return;
    selectField(fieldStamp, { render: false });
    state.resize = {
      fieldStamp,
      startX: Number(event.clientX || 0),
      startSize: Math.max(1, Number(target?.[getActiveWidthField()] || 1)),
      rowWidth: Math.max(1, row.getBoundingClientRect().width),
    };
    document.body.classList.add('spv-resizing');
    document.addEventListener('mousemove', handleResizeMove);
    document.addEventListener('mouseup', handleResizeEnd);
    event.preventDefault();
    event.stopPropagation();
  }

  async function loadDetail(menustamp, { silent = false } = {}) {
    const stamp = String(menustamp || '').trim();
    if (!stamp) {
      state.selectedMenustamp = '';
      state.detail = null;
      state.customObjects = [];
      state.variables = [];
      state.customObjectSeq = 0;
      state.selectedVariableStamp = '';
      state.selectedFieldStamp = '';
      state.selectedScope = 'screen';
      renderAll();
      setStatus('Seleciona um ecrã para visualizar o layout.');
      return;
    }

    state.loading = true;
    state.selectedMenustamp = stamp;
    if (!silent) setStatus('A carregar layout...');
    try {
      const params = new URLSearchParams({ menustamp: stamp });
      const detail = await fetchJson(`${cfg.layoutUrl}?${params.toString()}`);
      const hydrated = hydrateLoadedDetail(detail);
      state.detail = {
        menu: hydrated.menu,
        fields: hydrated.fields,
      };
      state.customObjects = hydrated.objects;
      state.variables = hydrated.variables;
      state.customObjectSeq = 0;
      state.selectedVariableStamp = getDefaultVariableStamp();
      normalizeListDesktopLayout();
      syncWidthModeFromMenu(state.detail.menu);
      state.selectedFieldStamp = getDefaultFieldStamp();
      state.selectedScope = getDefaultSelectionScope();
      renderAll();
      setStatus('Layout carregado. Arrasta a margem direita dos campos para ajustar a largura. Não gravado.');
    } catch (error) {
      state.detail = null;
      state.customObjects = [];
      state.variables = [];
      state.customObjectSeq = 0;
      state.selectedVariableStamp = '';
      state.selectedFieldStamp = '';
      state.selectedScope = 'screen';
      renderAll();
      setStatus(error.message || 'Erro ao carregar o layout.', 'danger');
      showToast(error.message || 'Erro ao carregar o layout.', 'error');
    } finally {
      state.loading = false;
    }
  }

  async function bootstrap() {
    setStatus('A carregar ecrãs...');
    try {
      const params = new URLSearchParams();
      if (state.selectedMenustamp) params.set('menustamp', state.selectedMenustamp);
      const payload = await fetchJson(`${cfg.bootstrapUrl}${params.toString() ? `?${params}` : ''}`);
      state.screens = Array.isArray(payload.screens) ? payload.screens.map(normalizeMenuRow) : [];
      state.sqlTables = Array.isArray(payload.sql_tables)
        ? payload.sql_tables.map((table) => ({
            key: String(table?.key || '').trim(),
            label: String(table?.label || table?.key || '').trim(),
            schema: String(table?.schema || '').trim(),
            table: String(table?.table || '').trim(),
          })).filter((table) => table.key)
        : [];
      state.selectedMenustamp = String(payload.selected_menustamp || state.selectedMenustamp || '').trim();
      if (payload.detail) {
        const hydrated = hydrateLoadedDetail(payload.detail);
        state.detail = {
          menu: hydrated.menu,
          fields: hydrated.fields,
        };
        state.customObjects = hydrated.objects;
        state.variables = hydrated.variables;
        state.customObjectSeq = 0;
        state.selectedVariableStamp = getDefaultVariableStamp();
        normalizeListDesktopLayout();
        syncWidthModeFromMenu(state.detail.menu);
        state.selectedFieldStamp = getDefaultFieldStamp();
        state.selectedScope = getDefaultSelectionScope();
      } else {
        state.detail = null;
        state.customObjects = [];
        state.variables = [];
        state.customObjectSeq = 0;
        state.selectedFieldStamp = '';
        state.selectedVariableStamp = '';
        state.selectedScope = 'screen';
      }
      renderAll();
      setStatus(state.screens.length ? 'Modo visualização. Arrasta a margem direita dos campos para ajustar a largura.' : 'Sem ecrãs genéricos disponíveis.');
    } catch (error) {
      setStatus(error.message || 'Erro ao carregar os ecrãs.', 'danger');
      showToast(error.message || 'Erro ao carregar os ecrãs.', 'error');
    }
  }

  els.screenSelect?.addEventListener('change', () => {
    loadDetail(String(els.screenSelect.value || '').trim());
  });

  els.formModeBtn?.addEventListener('click', () => {
    setLayoutMode('form');
  });

  els.listModeBtn?.addEventListener('click', () => {
    setLayoutMode('list');
  });

  els.desktopModeBtn?.addEventListener('click', () => {
    setViewportMode('desktop');
  });

  els.mobileModeBtn?.addEventListener('click', () => {
    setViewportMode('mobile');
  });

  els.exactWidthsBtn?.addEventListener('click', () => {
    setWidthMode(true);
  });

  els.proportionalWidthsBtn?.addEventListener('click', () => {
    setWidthMode(false);
  });

  els.sidebarFieldsBtn?.addEventListener('click', () => {
    if (state.sidebarMode === 'fields') return;
    state.sidebarMode = 'fields';
    state.selectedScope = getDefaultFieldStamp() ? 'field' : 'screen';
    renderAll();
  });

  els.sidebarObjectsBtn?.addEventListener('click', () => {
    if (state.sidebarMode === 'objects') return;
    state.sidebarMode = 'objects';
    state.selectedScope = getDefaultFieldStamp() ? 'field' : 'screen';
    renderAll();
  });

  els.sidebarVariablesBtn?.addEventListener('click', () => {
    if (state.sidebarMode === 'variables') return;
    state.sidebarMode = 'variables';
    ensureSelectedVariable();
    state.selectedScope = state.selectedVariableStamp ? 'variable' : getDefaultSelectionScope();
    renderAll();
  });

  els.sidebarAddBtn?.addEventListener('click', () => {
    if (state.sidebarMode === 'add') return;
    state.sidebarMode = 'add';
    renderAll();
  });

  els.sidebarCollapseBtn?.addEventListener('click', () => {
    state.sidebarCollapsed = !state.sidebarCollapsed;
    renderSidebarChrome();
    syncPreviewScaleHeight();
  });

  els.cancelBtn?.addEventListener('click', () => {
    loadDetail(state.selectedMenustamp, { silent: true });
  });

  els.fieldsList?.addEventListener('click', (event) => {
    const variableAction = event.target.closest('[data-variable-action="create"]');
    if (variableAction) {
      event.preventDefault();
      openVariableModal();
      return;
    }
    const variableCard = event.target.closest('.spv-field-card[data-variable-stamp]');
    if (variableCard) {
      state.selectedVariableStamp = String(variableCard.dataset.variableStamp || '').trim();
      state.selectedScope = 'variable';
      renderProperties();
      openVariableModal(state.selectedVariableStamp);
      return;
    }
    const card = event.target.closest('.spv-field-card[data-campostamp]');
    if (!card) return;
    selectField(String(card.dataset.campostamp || '').trim());
  });

  els.fieldsList?.addEventListener('mousedown', (event) => {
    const catalogCard = event.target.closest('.spv-field-card[data-object-template]');
    if (!catalogCard || Number(event.button) !== 0) return;
    beginFieldDrag('', event, {
      sourceKind: 'catalog',
      templateId: String(catalogCard.dataset.objectTemplate || '').trim(),
    });
  });

  els.fieldsList?.addEventListener('mousedown', (event) => {
    const fieldCard = event.target.closest('.spv-field-card[data-campostamp]');
    if (!fieldCard || Number(event.button) !== 0) return;
    const fieldStamp = String(fieldCard.dataset.campostamp || '').trim();
    const field = findFieldByStamp(fieldStamp);
    if (!field) return;
    beginFieldDrag(fieldStamp, event, {
      sourceKind: isVisibleField(field) ? 'layout' : 'sidebar',
    });
  });

  els.previewScale?.addEventListener('mousedown', (event) => {
    const handle = event.target.closest('.spv-resize-handle');
    if (handle) {
      beginResize(handle, event);
      return;
    }
    const field = event.target.closest('.spv-preview-field[data-campostamp]');
    if (!field || Number(event.button) !== 0) return;
    beginFieldDrag(String(field.dataset.campostamp || '').trim(), event);
  });

  els.previewScale?.addEventListener('click', (event) => {
    if (Date.now() < Number(state.suppressPreviewClickUntil || 0)) return;
    if (event.target.closest('.spv-resize-handle')) return;
    const field = event.target.closest('.spv-preview-field[data-campostamp]');
    if (!field) {
      selectScreen();
      return;
    }
    selectField(String(field.dataset.campostamp || '').trim());
  });

  els.propertiesContent?.addEventListener('input', (event) => {
    const input = event.target.closest('[data-prop-editor]');
    if (!input) return;
    const nextValue = input.type === 'checkbox' ? (input.checked ? 1 : 0) : input.value;
    updateSelectedFieldProperty(String(input.dataset.propEditor || '').trim(), nextValue);
  });

  els.propertiesContent?.addEventListener('change', (event) => {
    const input = event.target.closest('[data-prop-editor]');
    if (!input) return;
    const nextValue = input.type === 'checkbox' ? (input.checked ? 1 : 0) : input.value;
    updateSelectedFieldProperty(String(input.dataset.propEditor || '').trim(), nextValue);
    renderProperties();
  });

  els.propertiesContent?.addEventListener('click', (event) => {
    const eventEditorAction = event.target.closest('[data-event-editor]');
    if (eventEditorAction) {
      const eventName = String(eventEditorAction.dataset.eventEditor || 'click').trim().toLowerCase();
      if (state.selectedScope === 'screen') {
        openScreenEventEditor(eventName);
      } else {
        openFieldEventEditor(state.selectedFieldStamp, eventName);
      }
      return;
    }
    const action = event.target.closest('[data-variable-action]');
    if (!action) return;
    const kind = String(action.dataset.variableAction || '').trim();
    if (kind === 'edit-selected') {
      openVariableModal(state.selectedVariableStamp);
      return;
    }
    if (kind === 'delete-selected') {
      requestDeleteSelectedVariable();
    }
  });

  els.variableType?.addEventListener('change', () => {
    updateVariableTypeHint();
  });

  els.variableName?.addEventListener('blur', () => {
    if (!els.variableName) return;
    els.variableName.value = normalizeVariableName(els.variableName.value);
  });

  els.variableForm?.addEventListener('submit', (event) => {
    event.preventDefault();
    try {
      saveVariableFromModal();
    } catch (error) {
      const message = error?.message || 'Erro ao guardar a variavel.';
      setStatus(message, 'danger');
      showToast(message, 'error');
    }
  });

  els.variableDeleteBtn?.addEventListener('click', () => {
    requestDeleteSelectedVariable();
  });

  els.eventToolbox?.addEventListener('dragstart', (event) => {
    const command = event.target.closest('[data-event-command]');
    if (!command || !event.dataTransfer) return;
    state.eventDrag = null;
    event.dataTransfer.effectAllowed = 'copy';
    event.dataTransfer.setData('text/plain', String(command.dataset.eventCommand || '').trim().toUpperCase());
  });

  els.eventToolbox?.addEventListener('click', (event) => {
    const groupToggle = event.target.closest('[data-event-group-toggle]');
    if (groupToggle) {
      const groupId = String(groupToggle.dataset.eventGroupToggle || '').trim();
      state.eventToolboxOpenGroup = state.eventToolboxOpenGroup === groupId ? '' : groupId;
      renderEventToolbox();
      return;
    }
    const command = event.target.closest('[data-event-command]');
    if (!command || !state.eventEditor?.flow) return;
    const selectedIndex = findEventLineIndex(state.eventEditor.selectedLineId);
    const insertAt = selectedIndex >= 0 ? selectedIndex + 1 : getEventEditorLines().length;
    insertEventCommandAt(insertAt, String(command.dataset.eventCommand || '').trim().toUpperCase());
  });

  els.eventBuilder?.addEventListener('dragover', (event) => {
    const draggedLineId = String(
      state.eventDrag?.lineId
      || event.dataTransfer?.getData('application/x-spv-event-line')
      || '',
    ).trim();
    const command = String(event.dataTransfer?.getData('text/plain') || '').trim().toUpperCase();
    if (!draggedLineId && !EVENT_COMMAND_META[command]) return;
    const target = resolveEventDropTarget(event);
    if (!target) return;
    event.preventDefault();
    clearEventDropMarkers();
    target.marker?.classList.add(target.markerClass || 'is-over');
  });

  els.eventBuilder?.addEventListener('dragleave', (event) => {
    if (!els.eventBuilder?.contains(event.relatedTarget)) {
      clearEventDropMarkers();
    }
  });

  els.eventBuilder?.addEventListener('drop', (event) => {
    const draggedLineId = String(
      state.eventDrag?.lineId
      || event.dataTransfer?.getData('application/x-spv-event-line')
      || '',
    ).trim();
    const command = String(event.dataTransfer?.getData('text/plain') || '').trim().toUpperCase();
    const target = resolveEventDropTarget(event);
    clearEventDropMarkers();
    if (!target || (!draggedLineId && !EVENT_COMMAND_META[command])) return;
    event.preventDefault();
    if (draggedLineId) {
      moveEventLineToIndex(
        draggedLineId,
        target.slotIndex,
        { replaceEmpty: target.replaceEmpty },
      );
      state.eventDrag = null;
      return;
    }
    insertEventCommandAt(
      target.slotIndex,
      command,
      { replaceEmpty: target.replaceEmpty },
    );
  });

  els.eventBuilder?.addEventListener('dragstart', (event) => {
    const lineButton = event.target.closest('[data-event-line-id]');
    if (!lineButton || !event.dataTransfer) return;
    const line = findEventLineById(String(lineButton.dataset.eventLineId || '').trim());
    if (!canDragEventLine(line)) {
      event.preventDefault();
      return;
    }
    state.eventDrag = {
      lineId: String(lineButton.dataset.eventLineId || '').trim(),
    };
    event.dataTransfer.effectAllowed = 'move';
    event.dataTransfer.setData('application/x-spv-event-line', state.eventDrag.lineId);
  });

  els.eventBuilder?.addEventListener('dragend', () => {
    state.eventDrag = null;
    clearEventDropMarkers();
  });

  els.eventBuilder?.addEventListener('click', (event) => {
    const lineButton = event.target.closest('[data-event-line-id]');
    if (lineButton) {
      state.eventEditor.selectedLineId = String(lineButton.dataset.eventLineId || '').trim();
      renderEventBuilder();
      renderEventConfig();
    }
  });

  els.eventConfig?.addEventListener('input', (event) => {
    const schemaNameInput = event.target.closest('[data-event-cursor-schema-name]');
    if (schemaNameInput) {
      const key = String(schemaNameInput.dataset.eventCursorSchemaName || 'cursor_fields').trim();
      const index = Number(schemaNameInput.dataset.eventCursorSchemaIndex || -1);
      if (index >= 0) {
        updateSelectedEventCursorSchema(key, (schema) => {
          const next = schema.slice();
          next[index] = {
            ...(next[index] || {}),
            name: schemaNameInput.value,
          };
          return next;
        }, { rerenderConfig: false });
      }
      return;
    }
    const input = event.target.closest('[data-event-config-key]');
    if (!input) return;
    updateSelectedEventConfig(
      String(input.dataset.eventConfigKey || '').trim(),
      input.value,
      { rerenderConfig: false },
    );
  });

  els.eventConfig?.addEventListener('change', (event) => {
    const schemaTypeInput = event.target.closest('[data-event-cursor-schema-type]');
    if (schemaTypeInput) {
      const key = String(schemaTypeInput.dataset.eventCursorSchemaType || 'cursor_fields').trim();
      const index = Number(schemaTypeInput.dataset.eventCursorSchemaIndex || -1);
      if (index >= 0) {
        updateSelectedEventCursorSchema(key, (schema) => {
          const next = schema.slice();
          next[index] = {
            ...(next[index] || {}),
            type: schemaTypeInput.value,
          };
          return next;
        });
      }
      return;
    }
    const input = event.target.closest('[data-event-config-key]');
    if (!input) return;
    updateSelectedEventConfig(
      String(input.dataset.eventConfigKey || '').trim(),
      input.value,
      { rerenderConfig: true },
    );
  });

  els.eventConfig?.addEventListener('click', (event) => {
    const addCursorField = event.target.closest('[data-event-cursor-add]');
    if (addCursorField) {
      const key = String(addCursorField.dataset.eventCursorAdd || 'cursor_fields').trim();
      updateSelectedEventCursorSchema(key, (schema) => ([
        ...schema,
        { name: '', type: 'TEXT' },
      ]));
      return;
    }
    const removeCursorField = event.target.closest('[data-event-cursor-remove]');
    if (removeCursorField) {
      const key = String(removeCursorField.dataset.eventCursorRemove || 'cursor_fields').trim();
      const index = Number(removeCursorField.dataset.eventCursorSchemaIndex || -1);
      if (index >= 0) {
        updateSelectedEventCursorSchema(key, (schema) => schema.filter((_, itemIndex) => itemIndex !== index));
      }
      return;
    }
    const action = event.target.closest('[data-event-action]');
    if (!action) return;
    const kind = String(action.dataset.eventAction || '').trim();
    if (kind === 'remove-step') {
      removeSelectedEventLine();
    }
  });

  els.eventClearBtn?.addEventListener('click', () => {
    clearEventEditorFlow();
  });

  els.eventSaveBtn?.addEventListener('click', () => {
    saveEventEditor();
  });

  els.eventEditorModal?.addEventListener('hidden.bs.modal', () => {
    resetEventEditorState();
  });

  document.addEventListener('keydown', (event) => {
    if (event.key !== 'Delete') return;
    if (els.eventEditorModal?.classList.contains('show')) return;
    const active = document.activeElement;
    if (active && (
      active.matches('input, textarea, select, option, button') ||
      active.closest('[contenteditable="true"]')
    )) {
      return;
    }
    if (state.sidebarMode === 'variables' && findVariableByStamp(state.selectedVariableStamp)) {
      event.preventDefault();
      requestDeleteSelectedVariable();
      return;
    }
    if (!findKnownFieldByStamp(state.selectedFieldStamp)) return;
    event.preventDefault();
    requestDeleteSelectedField();
  });

  els.backBtn?.addEventListener('click', () => {
    if (window.history.length > 1) {
      window.history.back();
      return;
    }
    window.location.assign('/');
  });
  els.saveBtn?.addEventListener('click', () => {
    saveLayout();
  });

  if (els.variableType) {
    els.variableType.innerHTML = VARIABLE_TYPES.map((type) => {
      const meta = getVariableTypeMeta(type);
      return `<option value="${escapeHtml(type)}">${escapeHtml(meta.label)}</option>`;
    }).join('');
    els.variableType.value = 'TEXT';
  }
  updateVariableTypeHint();

  window.addEventListener('resize', syncPreviewScaleHeight);

  bootstrap();
});
