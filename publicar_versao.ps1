Write-Host "=============================="
Write-Host " PUBLICAR NOVA VERSAO DO SITE "
Write-Host "=============================="
Write-Host ""

try {
    Set-Location "C:\APP_WEB"

    if (!(Test-Path ".git")) {
        throw "A pasta C:\APP_WEB nao e um repositorio Git."
    }

    git --version | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Git nao esta instalado ou nao esta no PATH."
    }

    $mensagem = Read-Host "Mensagem para o commit"

    Write-Host ""
    Write-Host "--- STATUS ---"
    git status

    Write-Host ""
    Write-Host "--- ADD ---"
    git add .
    if ($LASTEXITCODE -ne 0) {
        throw "Erro no git add."
    }

    Write-Host ""
    Write-Host "--- COMMIT ---"
    git commit -m "$mensagem"

    if ($LASTEXITCODE -ne 0) {
        Write-Host "Nada para commit ou erro no commit." -ForegroundColor Yellow
    }

    Write-Host ""
    Write-Host "--- PUSH ---"
    git push origin master

    if ($LASTEXITCODE -ne 0) {
        throw "Erro no git push. Verifica login, permissao ou branch."
    }

    Write-Host ""
    Write-Host "Versao publicada com sucesso." -ForegroundColor Green
}
catch {
    Write-Host ""
    Write-Host "ERRO:" -ForegroundColor Red
    Write-Host $_ -ForegroundColor Red
}
finally {
    Write-Host ""
    Read-Host "Prima ENTER para fechar"
}