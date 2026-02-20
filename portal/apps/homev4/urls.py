from django.urls import path

from . import views

app_name = "homev4"

urlpatterns = [
    path("save/<int:layout_id>/", views.save_grid, name="save_grid"),
    path("reset/<int:layout_id>/", views.reset_grid, name="reset_grid"),
    path("sync/<int:layout_id>/", views.sync_sections, name="sync_sections"),
    path("api/sections/", views.sections_json, name="sections_json"),
    path("api/categories/", views.categories_json, name="categories_json"),
]
