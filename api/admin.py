"""
Configuración del Admin de Django
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Empleado, Encuesta, ResultadoEncuestas, RespuestasEncuesta, Notificacion


@admin.register(Empleado)
class EmpleadoAdmin(UserAdmin):
    """Configuración del admin para Empleado"""
    list_display = ('numero_empleado', 'nombre_completo', 'email', 'id_departamento', 'activo', 'creado_en')
    list_filter = ('activo', 'id_departamento', 'creado_en')
    search_fields = ('numero_empleado', 'nombre_completo', 'email')
    ordering = ('-creado_en',)
    
    fieldsets = UserAdmin.fieldsets + (
        ('Información Adicional', {'fields': ('id_departamento',)}),
    )
    
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Información Adicional', {'fields': ('numero_empleado', 'nombre_completo', 'id_departamento')}),
    )


@admin.register(Encuesta)
class EncuestaAdmin(admin.ModelAdmin):
    """Configuración del admin para Encuesta"""
    list_display = ('id', 'tipo', 'descripcion', 'activa', 'creado_en')
    list_filter = ('tipo', 'activa', 'creado_en')
    search_fields = ('descripcion',)
    ordering = ('-creado_en',)
    readonly_fields = ('creado_en', 'actualizado_en')


@admin.register(ResultadoEncuestas)
class ResultadoEncuestasAdmin(admin.ModelAdmin):
    """Configuración del admin para ResultadoEncuestas"""
    list_display = ('id', 'empleado', 'encuesta', 'estado', 'puntaje_total', 'nivel_riesgo', 'fecha_completado')
    list_filter = ('estado', 'nivel_riesgo', 'encuesta__tipo', 'creado_en')
    search_fields = ('empleado__numero_empleado', 'empleado__nombre_completo')
    ordering = ('-creado_en',)
    readonly_fields = ('creado_en', 'actualizado_en', 'enviado_en')


@admin.register(RespuestasEncuesta)
class RespuestasEncuestaAdmin(admin.ModelAdmin):
    """Configuración del admin para RespuestasEncuesta"""
    list_display = ('id', 'empleado', 'encuesta', 'sesion_id', 'contestadas_en')
    list_filter = ('encuesta__tipo', 'contestadas_en')
    search_fields = ('empleado__numero_empleado', 'sesion_id')
    ordering = ('-contestadas_en',)
    readonly_fields = ('creado_en', 'actualizado_en', 'contestadas_en')


@admin.register(Notificacion)
class NotificacionAdmin(admin.ModelAdmin):
    """Configuración del admin para Notificacion"""
    list_display = ('id', 'empleado', 'encuesta', 'email_destino', 'estado', 'enviado_en', 'intentos')
    list_filter = ('estado', 'creado_en')
    search_fields = ('email_destino', 'asunto')
    ordering = ('-creado_en',)
    readonly_fields = ('creado_en', 'actualizado_en')
