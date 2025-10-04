@echo off
echo DEPLOYING CLEAN LOCAL BACKEND TO UNRAID
echo ========================================
echo.

echo This script will:
echo 1. Backup the current corrupted backend on server
echo 2. Copy your clean local backend files to server
echo 3. Restart the backend container with clean files
echo.

echo STEP 1: Creating backup of current backend
echo ------------------------------------------
ssh root@192.168.254.14 "cp -r /mnt/user/appdata/watch1/backend /mnt/user/appdata/watch1/backend.backup.%date:~-4,4%%date:~-10,2%%date:~-7,2%"

echo.
echo STEP 2: Copying clean local backend to server
echo ---------------------------------------------
echo Copying backend directory...
scp -r p:\Watch1\backend\* root@192.168.254.14:/mnt/user/appdata/watch1/backend/

echo.
echo STEP 3: Creating clean requirements.txt
echo ---------------------------------------
ssh root@192.168.254.14 "cat > /mnt/user/appdata/watch1/backend/requirements.txt << 'EOF'
Flask==2.3.3
Flask-CORS==4.0.0
Flask-JWT-Extended==4.5.3
psycopg2-binary==2.9.7
python-dotenv==1.0.0
Werkzeug==2.3.7
bcrypt==4.0.1
Pillow==10.0.1
requests==2.31.0
PyYAML==6.0.1
mutagen==1.47.0
EOF"

echo.
echo STEP 4: Creating config directory and file
echo ------------------------------------------
ssh root@192.168.254.14 "mkdir -p /mnt/user/appdata/watch1/backend/config"
ssh root@192.168.254.14 "cat > /mnt/user/appdata/watch1/backend/config/watch_media_dirs.yml << 'EOF'
media_categories:
  movies:
    name: Movies
    extensions: [mp4, mkv, avi, mov]
    include_patterns: ['**/Movies/**']
  tv_shows:
    name: TV Shows  
    extensions: [mp4, mkv, avi, mov]
    include_patterns: ['**/TV/**']
  music:
    name: Music
    extensions: [mp3, flac, wav, aac]
    include_patterns: ['**/Music/**']
EOF"

echo.
echo STEP 5: Restarting backend with clean files
echo -------------------------------------------
ssh root@192.168.254.14 "docker rm -f watch1-backend"
ssh root@192.168.254.14 "docker run -d --name watch1-backend -p 8000:8000 -v /mnt/user/appdata/watch1/backend:/app -v /mnt/user/media:/app/media -w /app -e DB_HOST=watch1-db -e DB_USER=watch1_user -e DB_PASSWORD=watch1_password -e DB_NAME=watch1 --link watch1-db:watch1-db python:3.11-slim bash -c 'pip install -r requirements.txt && python main.py'"

echo.
echo STEP 6: Testing deployment
echo --------------------------
echo Waiting 30 seconds for backend to start...
timeout /t 30 /nobreak > nul
curl -s http://192.168.254.14:8000/health

echo.
echo DEPLOYMENT COMPLETE!
echo ===================
echo Your clean local backend has been deployed to the server.
echo Test at: http://192.168.254.14:3000
echo.

pause
