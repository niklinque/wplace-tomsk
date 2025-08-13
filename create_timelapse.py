#!/usr/bin/env python3
"""
Скрипт для создания видео-таймлапса из дампов изображений.
Собирает все изображения за день и создает видео на белом фоне.
"""

import os
import glob
import logging
import sys
from datetime import datetime, timedelta, timezone
from PIL import Image, ImageDraw
import cv2
import numpy as np

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Константы
OUTPUT_DIR = "output"
TIMELAPSE_DIR = "timelapse"
VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
FPS = 30  # 30 кадров в секунду
BACKGROUND_COLOR = (255, 255, 255)  # Белый фон
TOMSK_TZ = timezone(timedelta(hours=7))

def get_images_for_date(date_str):
    """
    Получает список изображений за указанную дату.
    
    Args:
        date_str (str): Дата в формате YYYYMMDD
        
    Returns:
        list: Список путей к файлам изображений
    """
    images = []
    
    date_folder = os.path.join(OUTPUT_DIR, date_str)
    if os.path.exists(date_folder):
        pattern = os.path.join(date_folder, "merged_tiles_*.png")
        folder_images = glob.glob(pattern)
        images.extend(folder_images)
        logger.info(f"В папке {date_str} найдено {len(folder_images)} изображений")
    
    # Сортируем по дате и времени из имени файла: merged_tiles_YYYYMMDD_HHMMSS.png
    def extract_timestamp_key(file_path):
        filename = os.path.basename(file_path)
        parts = filename.split('_')
        if len(parts) >= 4:
            date_part = parts[2]
            time_part = parts[3].split('.')[0]
            return f"{date_part}_{time_part}"
        return filename
    
    images.sort(key=extract_timestamp_key)
    
    logger.info(f"Всего найдено {len(images)} изображений за {date_str}")
    return images

def resize_image_to_fit(image, target_width, target_height, background_color=(255, 255, 255)):
    """
    Изменяет размер изображения с сохранением пропорций и добавляет белый фон.
    
    Args:
        image (PIL.Image): Исходное изображение
        target_width (int): Целевая ширина
        target_height (int): Целевая высота
        background_color (tuple): Цвет фона
        
    Returns:
        tuple: (PIL.Image, (x, y, new_width, new_height)) — изображение и позиция/размер вставленного контента
    """
    # Вычисляем коэффициент масштабирования для сохранения пропорций
    img_width, img_height = image.size
    scale_w = target_width / img_width
    scale_h = target_height / img_height
    scale = min(scale_w, scale_h)
    
    # Новые размеры с сохранением пропорций
    new_width = int(img_width * scale)
    new_height = int(img_height * scale)
    
    # Изменяем размер изображения
    resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    # Создаем новое изображение с белым фоном
    result = Image.new('RGB', (target_width, target_height), background_color)
    
    # Вычисляем позицию для центрирования
    x = (target_width - new_width) // 2
    y = (target_height - new_height) // 2
    
    # Вставляем изображение по центру
    if resized_image.mode == 'RGBA':
        result.paste(resized_image, (x, y), resized_image)
    else:
        result.paste(resized_image, (x, y))
    
    return result, (x, y, new_width, new_height)

def add_timestamp_overlay(image, timestamp, font_size=36):
    """
    Добавляет временную метку на изображение.
    
    Args:
        image (PIL.Image): Изображение
        timestamp (str): Временная метка
        font_size (int): Размер шрифта
        
    Returns:
        PIL.Image: Изображение с временной меткой
    """
    draw = ImageDraw.Draw(image)
    
    # Позиция для текста (нижний правый угол)
    text_position = (image.width - 300, image.height - 50)
    
    # Добавляем полупрозрачный фон для текста
    text_bbox = draw.textbbox(text_position, timestamp)
    draw.rectangle([text_bbox[0] - 10, text_bbox[1] - 5, text_bbox[2] + 10, text_bbox[3] + 5], 
                  fill=(0, 0, 0, 128))
    
    # Добавляем текст
    draw.text(text_position, timestamp, fill=(255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0))
    
    return image

def add_red_border(image, border_color=(255, 0, 0), border_thickness=4, box=None):
    """
    Добавляет красную рамку вокруг изображения.
    
    Args:
        image (PIL.Image): Изображение
        border_color (tuple): Цвет рамки в формате RGB
        border_thickness (int): Толщина рамки в пикселях
        
    Returns:
        PIL.Image: Изображение с рамкой
    """
    draw = ImageDraw.Draw(image)
    if box is None:
        x0, y0 = 0, 0
        x1, y1 = image.width - 1, image.height - 1
    else:
        x, y, w, h = box
        x0, y0 = x, y
        x1, y1 = x + w - 1, y + h - 1
    # Рисуем несколько прямоугольников внутрь для толщины рамки
    for offset in range(border_thickness):
        draw.rectangle(
            [
                (x0 + offset, y0 + offset),
                (x1 - offset, y1 - offset)
            ],
            outline=border_color
        )
    return image

def create_timelapse_video(images, output_path):
    """
    Создает видео-таймлапс из списка изображений.
    
    Args:
        images (list): Список путей к изображениям
        output_path (str): Путь для сохранения видео
        
    Returns:
        bool: True если успешно, False в случае ошибки
    """
    if not images:
        logger.error("Нет изображений для создания таймлапса")
        return False
    
    try:
        # Инициализируем видео writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        video_writer = cv2.VideoWriter(output_path, fourcc, FPS, (VIDEO_WIDTH, VIDEO_HEIGHT))
        
        logger.info(f"Создаю видео с {len(images)} кадрами, FPS: {FPS}")
        
        for i, image_path in enumerate(images):
            try:
                # Загружаем изображение
                pil_image = Image.open(image_path)
                
                # Извлекаем временную метку из имени файла
                filename = os.path.basename(image_path)
                # Формат: merged_tiles_YYYYMMDD_HHMMSS.png
                parts = filename.split('_')
                if len(parts) >= 3:
                    date_part = parts[2]
                    time_part = parts[3].split('.')[0]
                    timestamp = f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]} {time_part[:2]}:{time_part[2:4]}:{time_part[4:6]}"
                else:
                    timestamp = f"Кадр {i+1}"
                
                # Изменяем размер и добавляем на белый фон
                resized_image, placement = resize_image_to_fit(pil_image, VIDEO_WIDTH, VIDEO_HEIGHT, BACKGROUND_COLOR)
                
                # Добавляем временную метку
                final_image = add_timestamp_overlay(resized_image, timestamp)
                
                # Добавляем красную рамку вокруг области вставленного изображения (9000x9000 после масштабирования)
                final_image = add_red_border(final_image, box=placement)
                
                # Конвертируем PIL в OpenCV формат
                opencv_image = cv2.cvtColor(np.array(final_image), cv2.COLOR_RGB2BGR)
                
                # Записываем кадр в видео
                video_writer.write(opencv_image)
                
                if (i + 1) % 10 == 0:
                    logger.info(f"Обработано {i + 1}/{len(images)} кадров")
                    
            except Exception as e:
                logger.error(f"Ошибка при обработке изображения {image_path}: {e}")
                continue
        
        # Закрываем video writer
        video_writer.release()
        logger.info(f"Видео успешно создано: {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при создании видео: {e}")
        return False

def update_readme_with_timelapse_link(date_str, video_filename):
    """
    Обновляет README.md со ссылкой на последний созданный таймлапс.
    
    Args:
        date_str (str): Дата в формате YYYYMMDD
        video_filename (str): Имя файла видео
    """
    readme_path = "README.md"
    
    try:
        # Читаем текущий README
        with open(readme_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Форматируем дату для отображения
        formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        
        # Создаем ссылку на видео
        video_link = f"[🎬 Таймлапс за {formatted_date}](./timelapse/{video_filename})"
        
        # Проверяем, есть ли уже секция с последним таймлапсом
        timelapse_section_marker = "## 🎬 Последний таймлапс"
        
        if timelapse_section_marker in content:
            # Находим начало секции
            start_pos = content.find(timelapse_section_marker)
            # Находим конец секции (следующий заголовок или конец файла)
            next_section = content.find("\n## ", start_pos + 1)
            
            if next_section == -1:
                # Если это последняя секция, заменяем до конца файла
                new_content = content[:start_pos] + f"{timelapse_section_marker}\n\n{video_link}\n\n"
            else:
                # Заменяем секцию
                new_content = content[:start_pos] + f"{timelapse_section_marker}\n\n{video_link}\n\n" + content[next_section:]
        else:
            # Добавляем новую секцию в начало файла после заголовка
            lines = content.split('\n')
            
            # Находим первую строку, которая не является заголовком проекта
            insert_pos = 0
            for i, line in enumerate(lines):
                if line.startswith('# ') and i == 0:
                    continue
                if line.strip() == '':
                    continue
                insert_pos = i
                break
            
            # Вставляем секцию
            lines.insert(insert_pos, f"{timelapse_section_marker}\n")
            lines.insert(insert_pos + 1, f"{video_link}\n")
            new_content = '\n'.join(lines)
        
        # Записываем обновленный README
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        logger.info(f"README.md обновлен со ссылкой на таймлапс: {video_link}")
        
    except Exception as e:
        logger.error(f"Ошибка при обновлении README.md: {e}")

def main():
    """
    Основная функция скрипта.
    """
    # Создаем директорию для таймлапсов
    os.makedirs(TIMELAPSE_DIR, exist_ok=True)
    
    # Получаем вчерашнюю дату (так как скрипт обычно запускается на следующий день)
    yesterday = datetime.now(TOMSK_TZ) - timedelta(days=1)
    date_str = yesterday.strftime("%Y%m%d")
    
    logger.info(f"Создаю таймлапс за {date_str}")
    
    # Получаем список изображений за день
    images = get_images_for_date(date_str)
    
    if not images:
        logger.warning(f"Не найдено изображений за {date_str}")
        return False
    
    # Создаем имя выходного файла
    output_filename = f"timelapse_{date_str}.mp4"
    output_path = os.path.join(TIMELAPSE_DIR, output_filename)
    
    # Создаем таймлапс
    success = create_timelapse_video(images, output_path)
    
    if success:
        logger.info(f"Таймлапс успешно создан: {output_path}")
        
        # Также создаем ссылку на последний таймлапс
        latest_path = os.path.join(TIMELAPSE_DIR, "latest.mp4")
        if os.path.exists(latest_path):
            os.remove(latest_path)
        
        # Создаем копию как latest.mp4
        import shutil
        shutil.copy2(output_path, latest_path)
        logger.info(f"Создана копия как: {latest_path}")
        
        # Обновляем README.md со ссылкой на новый таймлапс
        update_readme_with_timelapse_link(date_str, output_filename)
        
        return True
    else:
        logger.error("Не удалось создать таймлапс")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
