param()

Write-Host "Running Watch1 Development Tests" -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan

# Run health check
Write-Host "
Health Check:" -ForegroundColor Yellow
python tools\health-monitor.py

# Run API tests  
Write-Host "
API Tests:" -ForegroundColor Yellow
python tools\api-tester.py

Write-Host "
Development tests complete!" -ForegroundColor Green
