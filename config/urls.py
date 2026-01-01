from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.conf import settings
from django.conf.urls.static import static

from game.views import deck_builder_page  # 👈 UI

urlpatterns = [
    path("admin/", admin.site.urls),

    path("api/auth/register/", include("accounts.urls")),
    path("api/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    # ✅ API
    path("api/game/", include("game.urls")),

    # ✅ UI
    path("deck/", deck_builder_page, name="deck_builder"),

    path("", include("webui.urls")),
]


# ✅ Servir archivos subidos (MEDIA) también en producción cuando no hay Nginx/S3.
# Render (sin disco persistente o storage externo) puede perder estos archivos tras redeploy;
# pero al menos se verán mientras existan en el filesystem del servicio.
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
