from django.core.paginator import Paginator


def get_paginated_page(queryset, page_number, per_page=12):
    paginator = Paginator(queryset, per_page)
    return paginator.get_page(page_number)
