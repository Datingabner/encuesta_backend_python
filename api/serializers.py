"""
Serializers para la API REST de Encuestas
"""
import re
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import authenticate
from .models import Empleado, Encuesta, ResultadoEncuestas, RespuestasEncuesta, Notificacion


class EmpleadoSerializer(serializers.ModelSerializer):
    """Serializer para el modelo Empleado"""
    
    class Meta:
        model = Empleado
        fields = ['id', 'numero_empleado', 'nombre_completo', 'email', 'id_departamento', 'activo']
        read_only_fields = ['id', 'creado_en', 'actualizado_en']


class TokenObtainPairSerializerCustom(TokenObtainPairSerializer):
    """Serializer personalizado para obtener tokens JWT"""
    
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        
        # Agregar claims personalizados
        token['id_empleado'] = user.id
        token['numero_empleado'] = user.numero_empleado
        token['nombre_completo'] = user.nombre_completo
        token['id_departamento'] = user.id_departamento
        
        return token
    
    def validate(self, attrs):
        # El autenticador ya valida el usuario
        return super().validate(attrs)


class ValidarEmpleadoSerializer(serializers.Serializer):
    """Serializer para validar empleado por número"""
    numero_empleado = serializers.CharField(max_length=20)
    
    def validate_numero_empleado(self, value):
        value = value.strip().upper()
        if not re.match(r'^[A-Z0-9]{4,20}$', value):
            raise serializers.ValidationError('Formato de número de empleado inválido')
        return value


class EncuestaSerializer(serializers.ModelSerializer):
    """Serializer para el modelo Encuesta"""
    
    class Meta:
        model = Encuesta
        fields = ['id', 'tipo', 'descripcion', 'preguntas', 'activa', 'creado_en', 'actualizado_en']
        read_only_fields = ['id', 'creado_en', 'actualizado_en']


class PreguntaSerializer(serializers.Serializer):
    """Serializer para preguntas de encuesta"""
    id_pregunta = serializers.IntegerField(required=False)
    pregunta = serializers.CharField()
    respuestas = serializers.ListField(child=serializers.IntegerField(), required=False)
    requerido = serializers.BooleanField(default=True)


class EncuestaDetailSerializer(serializers.ModelSerializer):
    """Serializer para obtener detalle de encuesta"""
    preguntas = PreguntaSerializer(many=True, read_only=True)
    
    class Meta:
        model = Encuesta
        fields = ['id', 'tipo', 'descripcion', 'preguntas', 'activa']


class RespuestaItemSerializer(serializers.Serializer):
    """Serializer para cada respuesta individual"""
    preguntas = serializers.ListField()
    respuestas = serializers.ListField(child=serializers.IntegerField())


class SubmitSurveySerializer(serializers.Serializer):
    """Serializer para enviar respuestas de encuesta"""
    responses = RespuestaItemSerializer(many=True)
    sessionId = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class ResultadoEncuestasSerializer(serializers.ModelSerializer):
    """Serializer para resultados de encuestas"""
    encuesta_nombre = serializers.SerializerMethodField()
    encuesta_tipo = serializers.CharField(source='encuesta.tipo', read_only=True)
    encuesta_descripcion = serializers.CharField(source='encuesta.descripcion', read_only=True)
    
    class Meta:
        model = ResultadoEncuestas
        fields = [
            'id', 'id_encuesta', 'encuesta_nombre', 'encuesta_tipo', 
            'encuesta_descripcion', 'estado', 'iniciado_en', 'fecha_completado',
            'enviado_en', 'tiene_puntaje', 'puede_tomar', 'puede_reintentar'
        ]
        read_only_fields = ['id', 'creado_en', 'actualizado_en']
    
    def get_encuesta_nombre(self, obj):
        tipo_nombres = {
            'ansiedad': 'Encuesta de Ansiedad (GAD-7)',
            'depresion': 'Encuesta de Depresión (PHQ-9)',
            'general': 'Encuesta General'
        }
        return tipo_nombres.get(obj.encuesta.tipo, 'Encuesta sin nombre')
    
    @property
    def tiene_puntaje(self):
        return self.instance.puntaje_total is not None if self.instance else False
    
    @property
    def puede_tomar(self):
        return self.instance.estado in ['pendiente', 'en_progreso'] if self.instance else True
    
    @property
    def puede_reintentar(self):
        if self.instance and self.instance.estado == 'completada' and self.instance.fecha_completado:
            from datetime import timedelta
            from django.utils import timezone
            treinta_dias = timezone.now().date() - timedelta(days=30)
            return self.instance.fecha_completado < treinta_dias
        return False


class ResultadoEncuestasDetailSerializer(serializers.ModelSerializer):
    """Serializer detallado para resultados"""
    empleado = EmpleadoSerializer(read_only=True)
    encuesta = EncuestaSerializer(read_only=True)
    
    class Meta:
        model = ResultadoEncuestas
        fields = [
            'id', 'empleado', 'encuesta', 'estado', 'puntaje_total',
            'interpretacion', 'nivel_riesgo', 'recomendaciones',
            'iniciado_en', 'fecha_completado', 'enviado_en'
        ]


class RespuestasEncuestaSerializer(serializers.ModelSerializer):
    """Serializer para respuestas de encuesta"""
    
    class Meta:
        model = RespuestasEncuesta
        fields = ['id', 'empleado', 'encuesta', 'preguntas', 'respuestas', 
                  'sesion_id', 'contestadas_en']
        read_only_fields = ['id', 'contestadas_en', 'creado_en', 'actualizado_en']


class NotificacionSerializer(serializers.ModelSerializer):
    """Serializer para notificaciones"""
    
    class Meta:
        model = Notificacion
        fields = [
            'id', 'empleado', 'encuesta', 'email_destino', 'asunto', 'cuerpo',
            'estado', 'enviado_en', 'mensaje_error', 'intentos'
        ]
        read_only_fields = ['id', 'creado_en', 'actualizado_en']


class ProgressStatsSerializer(serializers.Serializer):
    """Serializer para estadísticas de progreso"""
    total_encuestas = serializers.IntegerField()
    encuestas_completadas = serializers.IntegerField()
    en_progreso = serializers.IntegerField()
    pendientes = serializers.IntegerField()
    enviadas = serializers.IntegerField()


class SurveyResultSerializer(serializers.Serializer):
    """Serializer para resultados de encuesta (para admin)"""
    empleado = serializers.DictField()
    encuesta = serializers.DictField()
    detalle_clinico = serializers.DictField()
    puntaje_total = serializers.IntegerField(allow_null=True)
    interpretacion = serializers.CharField(allow_blank=True)
    nivel_riesgo = serializers.CharField(allow_blank=True)
    fecha_completado = serializers.DateField(allow_null=True)


class AdminStatsSerializer(serializers.Serializer):
    """Serializer para estadísticas administrativas"""
    total_completed = serializers.IntegerField()
    average_score = serializers.FloatField()
    distribucion_riesgo = serializers.DictField()
