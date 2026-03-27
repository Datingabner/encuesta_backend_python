"""
URLs de la API
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    ValidarEmpleadoView,
    TokenObtainPairViewCustom,
    EncuestaViewSet,
    EmpleadoViewSet,
    GetSurveyView,
    SubmitSurveyView,
    GetProgressView,
    GetResultsView,
    ValidateApiKeyView,
)

# Router para viewsets
router = DefaultRouter()
router.register(r'encuestas', EncuestaViewSet, basename='encuesta')
router.register(r'empleados', EmpleadoViewSet, basename='empleado')

urlpatterns = [
    # Auth endpoints
    path('auth/validar-empleado', ValidarEmpleadoView.as_view(), name='validar-empleado'),
    path('auth/token/', TokenObtainPairViewCustom.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # API Key validation endpoint
    path('api/admin/validate-key', ValidateApiKeyView.as_view(), name='validate-api-key'),
    path('api/validate-key/', ValidateApiKeyView.as_view(), name='validate-api-key'),

    
    # Survey endpoints
    path('encuestas/<int:survey_id>', GetSurveyView.as_view(), name='get-survey'),
    path('encuestas/<int:survey_id>/submit', SubmitSurveyView.as_view(), name='submit-survey'),
    
    # Employee endpoints
    path('empleado/progress', GetProgressView.as_view(), name='employee-progress'),
    
    # Admin endpoints
    path('admin/results', GetResultsView.as_view(), name='admin-results'),
    
    # Include router URLs
    path('', include(router.urls)),
]
