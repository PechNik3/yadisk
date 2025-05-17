import requests
from django.shortcuts import render
from typing import Optional

YANDEX_API_URL = 'https://cloud-api.yandex.net/v1/disk/public/resources'


def home(request):
    public_key = request.GET.get('public_key')
    files: Optional[list] = None

    if public_key:
        response = requests.get(YANDEX_API_URL, params={
            'public_key': public_key,
            'limit': 1000,
        })

        if response.status_code == 200:
            data = response.json()
            embedded = data.get('_embedded', {})
            items = embedded.get('items', [])
            files = [{
                'name': item['name'],
                'type': item['type'],
                'file': item.get('file')
            } for item in items]

    return render(request, 'files/home.html', {'files': files})
