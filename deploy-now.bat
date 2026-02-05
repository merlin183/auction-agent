@echo off
echo Railway Auto Deploy
railway login
railway link dda13b19-c392-456a-9b93-4eb146228f3e
set /p KEY="API Key: "
railway variables set ANTHROPIC_API_KEY="%KEY%"
railway variables set DEBUG="false"
railway add postgresql
railway add redis
echo Open: https://railway.app/project/dda13b19-c392-456a-9b93-4eb146228f3e
echo Connect GitHub: Settings - Source - Connect Repo - merlin183/auction-agent
pause
railway up
