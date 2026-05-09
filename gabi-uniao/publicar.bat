@echo off
cd /d "C:\Users\Carlos Vinicius\Documents\GitHub\dashboardgeral"
echo Adicionando arquivo...
git add gabi-uniao/index.html
echo Fazendo commit...
git commit -m "fix taxa compra vendasTraf/pv"
echo Publicando no GitHub...
git push
echo.
echo Pronto! Aguarde 1-2 minutos e atualize o Netlify.
pause
