# Скрипт для исправления кода на продакшене (PowerShell)

Write-Host "=== Исправление кода LONG_REPAIR на продакшене ===" -ForegroundColor Green

# Проверяем, что мы в правильной директории
if (-not (Test-Path "app/handlers/master.py")) {
    Write-Host "Ошибка: Файл app/handlers/master.py не найден" -ForegroundColor Red
    Write-Host "Убедитесь, что вы находитесь в корневой директории проекта" -ForegroundColor Red
    exit 1
}

# Создаем бэкап
Write-Host "Создаем бэкап файла master.py..." -ForegroundColor Yellow
Copy-Item "app/handlers/master.py" "app/handlers/master.py.backup"
Write-Host "Бэкап создан: app/handlers/master.py.backup" -ForegroundColor Green

# Проверяем, есть ли проблема в коде
$content = Get-Content "app/handlers/master.py" -Raw
if ($content -match "'LONG_REPAIR'") {
    Write-Host "Найдена проблема: хардкод 'LONG_REPAIR' в коде" -ForegroundColor Red
    
    # Исправляем код
    Write-Host "Исправляем код..." -ForegroundColor Yellow
    $fixedContent = $content -replace "'LONG_REPAIR'", "OrderStatus.DR"
    Set-Content "app/handlers/master.py" $fixedContent -Encoding UTF8
    
    # Проверяем исправление
    $newContent = Get-Content "app/handlers/master.py" -Raw
    if ($newContent -match "'LONG_REPAIR'") {
        Write-Host "Ошибка: Не удалось исправить код" -ForegroundColor Red
        exit 1
    } else {
        Write-Host "Код успешно исправлен!" -ForegroundColor Green
    }
} else {
    Write-Host "Код уже исправлен - хардкод 'LONG_REPAIR' не найден" -ForegroundColor Green
}

# Показываем статистику исправлений
Write-Host ""
Write-Host "Статистика исправлений:" -ForegroundColor Cyan
$drCount = (Select-String -Path "app/handlers/master.py" -Pattern "OrderStatus.DR").Count
$longRepairCount = (Select-String -Path "app/handlers/master.py" -Pattern "'LONG_REPAIR'").Count
Write-Host "  OrderStatus.DR в коде: $drCount" -ForegroundColor White
Write-Host "  'LONG_REPAIR' в коде: $longRepairCount" -ForegroundColor White

Write-Host ""
Write-Host "Исправление кода завершено!" -ForegroundColor Green
Write-Host "Теперь запустите: python fix_long_repair_production.py" -ForegroundColor Yellow
