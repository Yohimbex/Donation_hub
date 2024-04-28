from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.core.paginator import Paginator
from .models import Post, PostAlerts
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
from alerts_in_ua import Client as AlertsClient
from django.urls import reverse
from datetime import datetime
from django.conf import settings
import requests
import json
from django.http import HttpResponseBadRequest


def main_page(request):
    PostAlerts.objects.all().delete()
    if request.method == 'POST':
        if 'clear_posts' in request.POST:
            Post.objects.all().delete()
        else:
            query = request.POST.get('query')
            search_and_create_post(query, request)

    posts_list = Post.objects.order_by('-id')
    paginator = Paginator(posts_list, 3)

    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {'page_obj': page_obj}
    return render(request, 'donation_request_hub/home.html', context)


def search_and_create_post(query, request):
    api_key = settings.GOOGLE_API_KEY
    cse_id = settings.GOOGLE_CSE_ID
    max_posts = 6
    max_threads = 5

    try:
        existing_posts = set(Post.objects.values_list('source', flat=True))

        query = "Збір на " + query

        service = build("customsearch", "v1", developerKey=api_key)
        result = service.cse().list(
            q=query,
            cx=cse_id,
            num=10,
            fields='items(link, title, snippet)'
        ).execute()

        items = result.get('items', [])

        with ThreadPoolExecutor(max_workers=max_threads) as executor:
            futures = []
            for item in items:
                link = item['link']

                if len(existing_posts) >= max_posts:
                    break

                if link in existing_posts:
                    continue

                future = executor.submit(contains_monobank_jar_link, link)
                futures.append((future, item))

            for future, item in futures:
                monobank_jar_link = future.result()
                if monobank_jar_link:
                    if monobank_jar_link in existing_posts:
                        continue

                    post = Post.objects.create(
                        title=item['title'],
                        content=item['snippet'],
                        source=monobank_jar_link,
                    )

                    existing_posts.add(monobank_jar_link)

                    if len(existing_posts) >= max_posts:
                        break

        return JsonResponse({'success': True})

    except HttpError as e:
        print('An error occurred:', e)
        return JsonResponse({'success': False, 'message': 'An error occurred while searching.'})


def contains_monobank_jar_link(link):
    try:
        response = requests.get(link)
        soup = BeautifulSoup(response.text, 'html.parser')
        for a_tag in soup.find_all('a'):
            href = a_tag.get('href')
            if href and href.startswith('https://send.monobank.ua/jar'):
                return href
    except Exception as e:
        print('An error occurred while checking link:', e)

    return None


def foundations(request):
    return render(request, 'donation_request_hub/foundations.html', {'title': 'Foundations'})


def alerts(request):
    if request.method == 'POST':
        PostAlerts.objects.all().delete()
        region = request.POST.get('query', None)

        if region:
            region = region.capitalize()
            if "область" not in region:
                region += " область"

        # Завантаження списку областей з файлу JSON
        with open(settings.REGIONS_FILE_PATH, 'r', encoding='utf-8') as file:
            regions_data = json.load(file)

        regions_list = regions_data.get('regions', [])

        if region not in regions_list:
            content = "❌Невірна область❌"
            PostAlerts.objects.create(
                title="Мапа тривог України",
                content=content,
                source=f"https://alerts.in.ua/"
            )
            return redirect(reverse('donation_hub-alerts'))

        alerts_client = AlertsClient(token=settings.ALERTS_API_TOKEN)
        active_alerts = alerts_client.get_active_alerts()

        alerts_list = []

        translation = {
            'air_raid': '🚨Повітряна тривога🚨',
            'artillery_shelling': '💣Загроза артобстрілу💣',
            'urban_fights': '⚔️Загроза вуличних боїв⚔️',
            'chemical': '⚠️Хімічна загроза⚠️',
            'nuclear': '☢️Радіаційна загроза☢️'
        }

        for alert in active_alerts:
            alert.started_at = alert.started_at.strftime('%Y-%m-%d %H:%M:%S')
            alert.updated_at = alert.updated_at.strftime('%Y-%m-%d %H:%M:%S')
            alert.finished_at = alert.finished_at.strftime('%Y-%m-%d %H:%M:%S') if alert.finished_at else None

            if alert.location_title.lower() == region.lower():
                translated_alert_type = translation.get(alert.alert_type, alert.alert_type)
                alerts_list.append({
                    'location_title': alert.location_title,
                    'alert_type': translated_alert_type
                })

        if not alerts_list:
            content = f"{region}: Наразі немає повітряної тривоги ({datetime.now().strftime('%H:%M:%S %d.%m.%Y')})"
            PostAlerts.objects.create(
                title="Мапа тривог України",
                content=content,
                source=f"https://alerts.in.ua/"
            )
        else:
            for alert in alerts_list:
                content = f"{alert['location_title']}: {alert['alert_type']} ({datetime.now().strftime('%H:%M:%S %d.%m.%Y')})"
                PostAlerts.objects.create(
                    title="Мапа тривог України",
                    content=content,
                    source="https://alerts.in.ua/"
                )

        return redirect(reverse('donation_hub-alerts'))

    posts = PostAlerts.objects.all()
    return render(request, 'donation_request_hub/alerts.html', {'title': 'Alerts', 'posts': posts})


def about(request):
    return render(request, 'donation_request_hub/about.html', {'title': 'About'})
