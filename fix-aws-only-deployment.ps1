# PowerShell script to fix Kubrick for AWS-only deployment
Write-Host "🔧 Fixing Kubrick for AWS-only deployment..." -ForegroundColor Green

# Stop any running containers
Write-Host "Stopping containers..." -ForegroundColor Yellow
docker-compose down

# Copy AWS-only environment files
Write-Host "Setting up AWS-only environment files..." -ForegroundColor Yellow
Copy-Item "kubrick-api/.env.aws-only" "kubrick-api/.env" -Force
Copy-Item "kubrick-mcp/.env.aws-only" "kubrick-mcp/.env" -Force

Write-Host "✅ AWS-only configuration applied!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Update your AWS credentials in both .env files:" -ForegroundColor White
Write-Host "   - kubrick-api/.env" -ForegroundColor Gray
Write-Host "   - kubrick-mcp/.env" -ForegroundColor Gray
Write-Host ""
Write-Host "2. Build and start the containers:" -ForegroundColor White
Write-Host "   docker-compose build --no-cache" -ForegroundColor Gray
Write-Host "   docker-compose up" -ForegroundColor Gray
Write-Host ""
Write-Host "The system will now use only AWS Bedrock and AWS Transcribe!" -ForegroundColor Green