@echo off
title AegisBot Real Phone WhatsApp Tunnel (Cloudflare)
echo =====================================================================
echo    AegisBot -- Instant Real Phone WhatsApp Tunnel
echo =====================================================================
echo.
echo [*] Exposing local AegisBot (http://localhost:8000) to the internet...
echo [*] Look for the line below starting with:
echo.
echo     https://[random-name].trycloudflare.com
echo.
echo [*] Copy that URL and paste into Meta Developer Console:
echo.
echo     Callback URL: https://[your-name].trycloudflare.com/webhook/whatsapp
echo     Verify Token: aegisbot-verify
echo.
echo =====================================================================
echo.
"%~dp0cloudflared.exe" tunnel --url http://localhost:8000
pause
