#!/bin/bash

# Скрипт для исправления кода на продакшене

echo "=== Исправление кода LONG_REPAIR на продакшене ==="

# Проверяем, что мы в правильной директории
if [ ! -f "app/handlers/master.py" ]; then
    echo "Ошибка: Файл app/handlers/master.py не найден"
    echo "Убедитесь, что вы находитесь в корневой директории проекта"
    exit 1
fi

# Создаем бэкап
echo "Создаем бэкап файла master.py..."
cp app/handlers/master.py app/handlers/master.py.backup
echo "Бэкап создан: app/handlers/master.py.backup"

# Проверяем, есть ли проблема в коде
if grep -q "'LONG_REPAIR'" app/handlers/master.py; then
    echo "Найдена проблема: хардкод 'LONG_REPAIR' в коде"
    
    # Исправляем код
    echo "Исправляем код..."
    sed -i "s/'LONG_REPAIR'/OrderStatus.DR/g" app/handlers/master.py
    
    # Проверяем исправление
    if grep -q "'LONG_REPAIR'" app/handlers/master.py; then
        echo "Ошибка: Не удалось исправить код"
        exit 1
    else
        echo "Код успешно исправлен!"
    fi
else
    echo "Код уже исправлен - хардкод 'LONG_REPAIR' не найден"
fi

# Показываем статистику исправлений
echo ""
echo "Статистика исправлений:"
echo "  OrderStatus.DR в коде: $(grep -c "OrderStatus.DR" app/handlers/master.py)"
echo "  'LONG_REPAIR' в коде: $(grep -c "'LONG_REPAIR'" app/handlers/master.py)"

echo ""
echo "Исправление кода завершено!"
echo "Теперь запустите: python fix_long_repair_production.py"
