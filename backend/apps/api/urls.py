# apps/api/urls.py
from .views import tender_download_excel_view

from django.urls import path
from .views import (
    parse_tender_zip_view,
    tender_status_view,
    tender_list_view,
)

urlpatterns = [
    path("tender/parse-zip/", parse_tender_zip_view),
    path("tender/status/", tender_status_view),
    path("tender/list/", tender_list_view),
    path("tender/download-excel/", tender_download_excel_view),
]
