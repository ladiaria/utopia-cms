from django.urls import path

from . import views

app_name = "homev4"

urlpatterns = [
    path("save/<int:layout_id>/", views.save_grid, name="save_grid"),
    path("reset/<int:layout_id>/", views.reset_grid, name="reset_grid"),
    path("sync/<int:layout_id>/", views.sync_sections, name="sync_sections"),
    path("sections/", views.sections_json, name="sections_json"),
    path("categories/", views.categories_json, name="categories_json"),
    path("article-search/", views.article_search, name="article_search"),
    path("newsletter-search/", views.newsletter_search, name="newsletter_search"),
    path("active-layout/", views.active_layout, name="active_layout"),
    path("active-layout/<slug:publication_slug>/", views.active_layout, name="active_layout_pub"),
    path("preview-5am/", views.preview_5am, name="preview_5am"),
    path("preview-5am-render/", views.preview_5am_render, name="preview_5am_render"),
    path("save-preview-session/", views.save_preview_session, name="save_preview_session"),
    path("save-pending/", views.save_pending_grid, name="save_pending_grid"),
    path("reset-pending/", views.reset_pending_grid, name="reset_pending_grid"),
]
