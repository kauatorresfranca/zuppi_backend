from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('social.urls')),  # Alterado de 'zuppi_app.urls' para 'social.urls'
]