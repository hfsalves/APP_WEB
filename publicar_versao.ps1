Write-Host "=============================="
Write-Host " PUBLICAR NOVA VERSÃO DO SITE "
Write-Host "==============================`n"

$mensagem = Read-Host "Mensagem para o commit"

git add .
git commit -m "$mensagem"
git push origin master

Write-Host "`nVersão publicada com sucesso."
pause
