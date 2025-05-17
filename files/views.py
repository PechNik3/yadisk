import os
import tempfile
import zipfile
import requests
from typing import Optional, List, Dict
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpRequest, HttpResponse
from django.core.cache import cache

YANDEX_API_URL = 'https://cloud-api.yandex.net/v1/disk/public/resources'


def filter_items_by_type(items: List[Dict], filter_type: str) -> List[Dict]:
    """
    Фильтрует список файлов по типу (images, documents, videos и т.д.)
    """
    if filter_type == 'all':
        return items

    mime_map = {
        'images': lambda m: m.startswith('image/'),
        'videos': lambda m: m.startswith('video/'),
        'documents': lambda m: m.startswith('application/') and any(ext in m for ext in [
            'pdf', 'msword', 'vnd.openxmlformats'])
    }

    checker = mime_map.get(filter_type)
    if not checker:
        return items

    return [item for item in items if 'mime_type' in item and checker(item['mime_type'])]


def get_yadisk_items(public_key: str) -> List[Dict]:
    """
    Получает список файлов по публичной ссылке с кэшированием (5 мин)
    """
    cache_key = f'yadisk:{public_key}'
    cached = cache.get(cache_key)

    if cached is not None:
        return cached

    response = requests.get(YANDEX_API_URL, params={
        'public_key': public_key,
        'limit': 1000,
    })

    if response.status_code != 200:
        return []

    data = response.json()
    items = data.get('_embedded', {}).get('items', [])

    cache.set(cache_key, items, timeout=300)
    return items


def generate_zip_from_urls(urls: List[str], names: List[str]) -> Optional[bytes]:
    """
    Скачивает файлы по URL и собирает zip-архив, возвращает байты архива
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = os.path.join(tmpdir, 'archive.zip')
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for url, name in zip(urls, names):
                try:
                    r = requests.get(url)
                    if r.status_code == 200:
                        zipf.writestr(name, r.content)
                except Exception:
                    pass

        if os.path.exists(zip_path):
            with open(zip_path, 'rb') as f:
                return f.read()

    return None


@csrf_exempt
def home(request: HttpRequest):
    public_key: Optional[str] = request.GET.get('public_key')
    filter_type: str = request.GET.get('type', 'all')
    files: Optional[List[Dict]] = None

    if public_key:
        # Загружаем и фильтруем список файлов
        items = get_yadisk_items(public_key)
        filtered = filter_items_by_type(items, filter_type)

        files = [{
            'name': item['name'],
            'type': item['type'],
            'file': item.get('file')
        } for item in filtered]

    if request.method == 'POST':
        selected_files = request.POST.getlist('selected_files')
        file_names = request.POST.getlist('file_names')

        if selected_files and file_names:
            zip_bytes = generate_zip_from_urls(selected_files, file_names)
            if zip_bytes:
                response = HttpResponse(zip_bytes, content_type='application/zip')
                response['Content-Disposition'] = 'attachment; filename=selected_files.zip'
                return response

    return render(request, 'files/home.html', {
        'files': files,
        'public_key': public_key or '',
        'selected_type': filter_type
    })
