#!/usr/bin/env python3
"""
Скрипт для автоматической организации тайлов по датам
Перемещает все тайлы в папки с соответствующими датами
"""

import os
import shutil
from datetime import datetime
import glob

def organize_tiles():
    """Организует тайлы по папкам с датами"""
    
    # Создаем папку output если её нет
    if not os.path.exists('output'):
        print("Папка output не найдена")
        return
    
    # Получаем текущую дату
    today = datetime.now().strftime('%Y%m%d')
    today_folder = os.path.join('output', today)
    
    # Создаем папку для сегодняшней даты
    os.makedirs(today_folder, exist_ok=True)
    print(f"Создана папка: {today_folder}")
    
    # Ищем все файлы тайлов в output (но не в подпапках)
    tile_files = []
    for ext in ['*.png', '*.jpg', '*.jpeg', '*.tiff', '*.bmp']:
        tile_files.extend(glob.glob(os.path.join('output', ext)))
    
    # Фильтруем только файлы (не папки)
    tile_files = [f for f in tile_files if os.path.isfile(f)]
    
    if not tile_files:
        print("Тайлы для организации не найдены")
        print("Возможно, они уже организованы по папкам")
        return
    
    # Перемещаем файлы в папку с датой
    moved_count = 0
    for tile_file in tile_files:
        filename = os.path.basename(tile_file)
        destination = os.path.join(today_folder, filename)
        
        try:
            shutil.move(tile_file, destination)
            print(f"Перемещен: {filename} -> {today_folder}/")
            moved_count += 1
        except Exception as e:
            print(f"Ошибка при перемещении {filename}: {e}")
    
    # Создаем README файл с информацией
    readme_path = os.path.join(today_folder, 'README.md')
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(f"# Тайлы за {today}\n\n")
        f.write(f"Дата создания: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Количество файлов: {moved_count}\n\n")
        f.write("## Список файлов:\n")
        for tile_file in sorted(glob.glob(os.path.join(today_folder, '*'))):
            if os.path.isfile(tile_file) and not tile_file.endswith('README.md'):
                f.write(f"- {os.path.basename(tile_file)}\n")
    
    print(f"\nОрганизация завершена!")
    print(f"Перемещено файлов: {moved_count}")
    print(f"Создан README: {readme_path}")

if __name__ == "__main__":
    organize_tiles()
