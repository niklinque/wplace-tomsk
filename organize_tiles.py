#!/usr/bin/env python3
"""
Скрипт для автоматической организации тайлов по датам
Анализирует имена файлов для определения даты и перемещает их в соответствующие папки
"""

import os
import shutil
import re
from datetime import datetime
import glob

def extract_date_from_filename(filename):
    """
    Извлекает дату из имени файла
    Поддерживает форматы: YYYYMMDD, YYYY-MM-DD, YYYY_MM_DD
    """
    # Убираем расширение файла
    name_without_ext = os.path.splitext(filename)[0]
    
    # Паттерны для поиска дат в имени файла
    patterns = [
        r'(\d{4})(\d{2})(\d{2})',  # YYYYMMDD
        r'(\d{4})-(\d{2})-(\d{2})',  # YYYY-MM-DD
        r'(\d{4})_(\d{2})_(\d{2})',  # YYYY_MM_DD
        r'(\d{4})\.(\d{2})\.(\d{2})',  # YYYY.MM.DD
    ]
    
    for pattern in patterns:
        match = re.search(pattern, name_without_ext)
        if match:
            year, month, day = match.groups()
            # Проверяем валидность даты
            try:
                datetime(int(year), int(month), int(day))
                return f"{year}{month}{day}"
            except ValueError:
                continue
    
    return None

def organize_tiles():
    """Организует тайлы по папкам с датами, извлеченными из имен файлов"""
    
    # Создаем папку output если её нет
    if not os.path.exists('output'):
        print("Папка output не найдена")
        return
    
    # Ищем все файлы тайлов в output (включая подпапки)
    tile_files = []
    for ext in ['*.png', '*.jpg', '*.jpeg', '*.tiff', '*.bmp']:
        # Ищем во всех подпапках output
        tile_files.extend(glob.glob(os.path.join('output', '**', ext), recursive=True))
    
    # Фильтруем только файлы (не папки)
    tile_files = [f for f in tile_files if os.path.isfile(f)]
    
    if not tile_files:
        print("Тайлы для организации не найдены")
        return
    
    print(f"Найдено файлов для анализа: {len(tile_files)}")
    
    # Группируем файлы по датам
    files_by_date = {}
    files_without_date = []
    
    for tile_file in tile_files:
        filename = os.path.basename(tile_file)
        date = extract_date_from_filename(filename)
        
        if date:
            if date not in files_by_date:
                files_by_date[date] = []
            files_by_date[date].append(tile_file)
        else:
            files_without_date.append(tile_file)
    
    print(f"Найдено дат: {len(files_by_date)}")
    if files_without_date:
        print(f"Файлов без даты: {len(files_without_date)}")
    
    # Перемещаем файлы по датам
    total_moved = 0
    
    for date, files in files_by_date.items():
        date_folder = os.path.join('output', date)
        os.makedirs(date_folder, exist_ok=True)
        print(f"Обрабатываем дату: {date} ({len(files)} файлов)")
        
        moved_count = 0
        for tile_file in files:
            filename = os.path.basename(tile_file)
            destination = os.path.join(date_folder, filename)
            
            # Проверяем, не существует ли уже файл с таким именем
            if os.path.exists(destination):
                base, ext = os.path.splitext(filename)
                counter = 1
                while os.path.exists(destination):
                    destination = os.path.join(date_folder, f"{base}_{counter}{ext}")
                    counter += 1
            
            try:
                shutil.move(tile_file, destination)
                print(f"  Перемещен: {filename} -> {date}/")
                moved_count += 1
            except Exception as e:
                print(f"Ошибка при перемещении {filename}: {e}")
        
        total_moved += moved_count
        
        # Создаем README файл с информацией
        readme_path = os.path.join(date_folder, 'README.md')
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(f"# Тайлы за {date}\n\n")
            f.write(f"Дата: {date[:4]}-{date[4:6]}-{date[6:8]}\n")
            f.write(f"Дата обработки: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Количество файлов: {moved_count}\n\n")
            f.write("## Список файлов:\n")
            for file_path in sorted(glob.glob(os.path.join(date_folder, '*'))):
                if os.path.isfile(file_path) and not file_path.endswith('README.md'):
                    f.write(f"- {os.path.basename(file_path)}\n")
    
    # Обрабатываем файлы без даты (оставляем в корне output)
    if files_without_date:
        print(f"\nФайлы без даты остались в корне папки output:")
        for file_path in files_without_date:
            print(f"  - {os.path.basename(file_path)}")
    
    print(f"\nОрганизация завершена!")
    print(f"Всего перемещено файлов: {total_moved}")
    print(f"Обработано дат: {len(files_by_date)}")

if __name__ == "__main__":
    organize_tiles()
