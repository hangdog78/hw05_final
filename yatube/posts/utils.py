from django.core.paginator import Page, Paginator

from django.conf import settings


def _get_page(request, posts) -> Page:
    paginator = Paginator(posts, settings.PAGE_SIZE)
    page_num = request.GET.get('page')
    page_obj = paginator.get_page(page_num)
    return page_obj
