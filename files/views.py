import requests
from django.shortcuts import render
from typing import Optional, List, Dict

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


def home(request):
    public_key: Optional[str] = request.GET.get('public_key')
    filter_type: str = request.GET.get('type', 'all')
    files: Optional[List[Dict]] = None

    if public_key:
        response = requests.get(YANDEX_API_URL, params={
            'public_key': public_key,
            'limit': 1000,
        })

        if response.status_code == 200:
            data = response.json()
            embedded = data.get('_embedded', {})
            items = embedded.get('items', [])

            # Фильтрация и сбор нужных полей
            filtered_items = filter_items_by_type(items, filter_type)

            files = [{
                'name': item['name'],
                'type': item['type'],
                'file': item.get('file')
            } for item in filtered_items]

    return render(request, 'files/home.html', {
        'files': files,
        'public_key': public_key or '',
        'selected_type': filter_type
    })
