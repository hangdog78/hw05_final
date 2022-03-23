from django.core.paginator import Page


def _get_page(request, paginator) -> Page:
    page_num = request.GET.get('page')
    page_obj = paginator.get_page(page_num)
    return page_obj
