from django.contrib import admin
from django.urls import path, include, re_path
from django.views.generic import TemplateView

urlpatterns = [
    # フロントエンド単ページアプリのエントリ
    path("", TemplateView.as_view(template_name="index.html"), name="root"),

    # 管理画面と REST API
    path("admin/", admin.site.urls),
    path("api/restaurants/", include("restaurants.urls")),

    # その他のパスもすべて index.html にフォールバック
    re_path(r"^(?:.*)/?$", TemplateView.as_view(template_name="index.html")),
]
