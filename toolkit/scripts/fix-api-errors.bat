@echo off
echo FIXING PERMISSIONS-POLICY AND API ERRORS
echo =========================================
echo.

echo The errors you're seeing are:
echo 1. permissions-policy header: browsing-topics issue
echo 2. VersionInfo.vue:72 failed to load
echo 3. GET request in media.ts failing  
echo 4. POST request in auth.ts failing
echo.

echo SOLUTION:
echo ----------
echo These are all related to:
echo - Missing/incorrect permissions-policy header
echo - Backend API endpoints not responding
echo - CORS configuration issues
echo.

echo TO FIX:
echo 1. SSH into your Unraid server: ssh root@192.168.254.14
echo 2. Run these commands:
echo.

echo    # Fix permissions-policy header
echo    docker exec watch1-frontend sed -i 's/usb=()/usb=(), browsing-topics=()/' /usr/share/nginx/html/index.html
echo.

echo    # Restart backend
echo    docker restart watch1-backend
echo.

echo    # Wait 30 seconds, then test
echo    curl -s http://192.168.254.14:8000/health
echo.

echo    # Test auth endpoint
echo    curl -X POST http://192.168.254.14:8000/api/v1/auth/login/access-token \
echo      -H "Content-Type: application/json" \
echo      -d '{"username":"test@example.com","password":"testpass123"}'
echo.

echo 3. Open http://192.168.254.14:3000 in browser
echo 4. Check browser console (F12) for remaining errors
echo.

echo If PowerShell continues having issues, use Windows Terminal or PuTTY instead.
echo.

pause
