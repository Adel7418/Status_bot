# Скрипт для создания резервной копии базы данных
# Использование: .\backup_db.ps1

param(
    [int]$KeepDays = 30  # Хранить копии за последние N дней
)

$ErrorActionPreference = "Stop"

# Путь к базе данных
$DbFile = "bot_database.db"
$BackupDir = "backups"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  РЕЗЕРВНОЕ КОПИРОВАНИЕ БАЗЫ ДАННЫХ" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Проверка существования БД
if (!(Test-Path $DbFile)) {
    Write-Host "Ошибка: Файл $DbFile не найден!" -ForegroundColor Red
    exit 1
}

# Создание директории для backup, если не существует
if (!(Test-Path $BackupDir)) {
    Write-Host "Создание директории: $BackupDir" -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $BackupDir | Out-Null
}

# Получение размера БД
$DbSize = (Get-Item $DbFile).Length
$DbSizeKB = [math]::Round($DbSize / 1KB, 2)

Write-Host "База данных: $DbFile" -ForegroundColor White
Write-Host "Размер: $DbSizeKB KB`n" -ForegroundColor White

# Создание имени файла с датой и временем
$Timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$BackupFile = Join-Path $BackupDir "bot_database_$Timestamp.db"

# Создание резервной копии
Write-Host "Создание резервной копии..." -ForegroundColor Yellow
try {
    Copy-Item $DbFile -Destination $BackupFile -Force
    Write-Host "Резервная копия создана!" -ForegroundColor Green
    Write-Host "Файл: $BackupFile`n" -ForegroundColor Green
}
catch {
    Write-Host "Ошибка при создании копии: $_" -ForegroundColor Red
    exit 1
}

# Подсчет всех резервных копий
$AllBackups = Get-ChildItem $BackupDir -Filter "bot_database_*.db" | Sort-Object LastWriteTime -Descending
$BackupCount = $AllBackups.Count

Write-Host "Всего резервных копий: $BackupCount" -ForegroundColor Cyan

# Удаление старых копий
$CutoffDate = (Get-Date).AddDays(-$KeepDays)
$OldBackups = Get-ChildItem $BackupDir -Filter "bot_database_*.db" | 
    Where-Object { $_.LastWriteTime -lt $CutoffDate }

if ($OldBackups.Count -gt 0) {
    Write-Host "`nУдаление старых копий (старше $KeepDays дней)..." -ForegroundColor Yellow
    
    foreach ($backup in $OldBackups) {
        Write-Host "  Удаление: $($backup.Name)" -ForegroundColor Gray
        Remove-Item $backup.FullName -Force
    }
    
    Write-Host "Удалено старых копий: $($OldBackups.Count)" -ForegroundColor Green
}

# Список последних резервных копий
Write-Host "`nПоследние 5 резервных копий:" -ForegroundColor Cyan
Get-ChildItem $BackupDir -Filter "bot_database_*.db" | 
    Sort-Object LastWriteTime -Descending | 
    Select-Object -First 5 | 
    Format-Table Name, @{Label="Размер (KB)"; Expression={[math]::Round($_.Length/1KB, 2)}}, LastWriteTime -AutoSize

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "            ГОТОВО!" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Cyan

