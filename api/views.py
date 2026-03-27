"""
Vistas (Views) para la API REST de Encuestas
"""
import json
import logging
import os
import threading
import uuid
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from django.db.models import Avg, Count, Q
from rest_framework import status, viewsets, generics
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import AllowAny, IsAuthenticated, BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from .models import Empleado, Encuesta, ResultadoEncuestas, RespuestasEncuesta, Notificacion
from .serializers import (
    TokenObtainPairSerializerCustom,
    ValidarEmpleadoSerializer,
    EmpleadoSerializer,
    EmpleadoCreateSerializer,
    EncuestaSerializer,
    EncuestaDetailSerializer,
    SubmitSurveySerializer,
    ResultadoEncuestasSerializer,
    ResultadoEncuestasDetailSerializer,
    ProgressStatsSerializer,
    SurveyResultSerializer,
    AdminStatsSerializer,
    NotificacionSerializer,
)

logger = logging.getLogger(__name__)


# ============== Custom Permissions ==============

class APIKeyPermission(BasePermission):
    """
    Permiso personalizado para autenticación via API Key
    Se usa para endpoints de Admin/RH
    """
    message = 'Acceso denegado. Se requieren credenciales de RRHH válidas.'
    
    def has_permission(self, request, view):
        # Obtener API Key del header o query params
        api_key = request.headers.get('x-api-key') or request.query_params.get('api_key')
        
        # Obtener la API Key configurada en settings
        admin_api_key = getattr(settings, 'ADMIN_API_KEY', '')
        
        # Verificar que ambas API Keys existan y coincidan
        if not api_key or not admin_api_key:
            return False
        
        return api_key == admin_api_key


# ============== Auth Views ==============

class ValidarEmpleadoView(APIView):
    """Validar número de empleado y generar token JWT"""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ValidarEmpleadoSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'error': serializer.errors.get('numero_empleado', ['Número de empleado requerido'])[0]
            }, status=status.HTTP_400_BAD_REQUEST)

        numero_empleado = serializer.validated_data['numero_empleado']
        
        try:
            empleado = Empleado.objects.get(
                numero_empleado=numero_empleado,
                activo=True
            )
        except Empleado.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Empleado no encontrado o inactivo'
            }, status=status.HTTP_404_NOT_FOUND)

        # Generar token JWT
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(empleado)
        
        return Response({
            'success': True,
            'message': 'Empleado validado exitosamente',
            'data': {
                'empleado': {
                    'id': empleado.id,
                    'numero_empleado': empleado.numero_empleado,
                    'nombre': empleado.nombre_completo,
                    'departamento': empleado.id_departamento
                },
                'token': str(refresh.access_token),
                'expires_in': '24h'
            }
        })


class TokenObtainPairViewCustom(TokenObtainPairView):
    """Vista personalizada para obtener token JWT"""
    serializer_class = TokenObtainPairSerializerCustom


# ============== Survey Views ==============

class EncuestaViewSet(viewsets.ModelViewSet):
    """ViewSet para encuestas (Admin/RH)"""
    queryset = Encuesta.objects.all()
    serializer_class = EncuestaSerializer
    permission_classes = [APIKeyPermission]
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return EncuestaDetailSerializer
        return EncuestaSerializer
    
    def get_queryset(self):
        if self.action == 'list':
            return Encuesta.objects.filter(activa=True)
        return Encuesta.objects.all()


class GetSurveyView(APIView):
    """Obtener una encuesta específica"""
    permission_classes = [IsAuthenticated]

    def get(self, request, survey_id):
        try:
            survey = Encuesta.objects.get(id=survey_id, activa=True)
        except Encuesta.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Encuesta no encontrada'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Registrar progreso
        try:
            ResultadoEncuestas.record_progress(
                request.user.id, 
                survey.id,
                {'estado': 'en_progreso'}
            )
        except Exception as e:
            logger.error(f"Error al registrar progreso: {e}")
        
        # Preparar preguntas
        preguntas_data = []
        for q in survey.preguntas:
            preguntas_data.append({
                'id_pregunta': q.get('id'),
                'pregunta': q.get('pregunta', ''),
                'respuestas': q.get('respuestas', []),
                'requerido': q.get('required', True)
            })
        
        return Response({
            'success': True,
            'data': {
                'id': survey.id,
                'tipo': survey.tipo,
                'descripcion': survey.descripcion,
                'preguntas': preguntas_data
            }
        })


class SubmitSurveyView(APIView):
    """Enviar respuestas de una encuesta"""
    permission_classes = [IsAuthenticated]

    def post(self, request, survey_id):
        serializer = SubmitSurveySerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'error': 'Se requieren respuestas válidas'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validar encuesta
        try:
            survey = Encuesta.objects.get(id=survey_id, activa=True)
        except Encuesta.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Encuesta no encontrada'
            }, status=status.HTTP_404_NOT_FOUND)
        
        responses = serializer.validated_data['responses']
        session_id = serializer.validated_data.get('sessionId') or f"session_{timezone.now().timestamp()}_{uuid.uuid4().hex[:9]}"
        
        # Calcular puntaje
        score = self._calculate_score(responses)
        interpretation = self._get_interpretation(survey.tipo, score)
        nivel_riesgo = self._get_nivel_riesgo(interpretation)
        
        # Guardar respuestas
        RespuestasEncuesta.save_batch(request.user.id, survey.id, responses, session_id)
        
        # Actualizar progreso
        ResultadoEncuestas.record_progress(
            request.user.id, 
            survey.id,
            {
                'estado': 'completada',
                'puntaje_total': score,
                'interpretacion': interpretation,
                'nivel_riesgo': nivel_riesgo,
                'recomendaciones': 'Consultar con el departamento de RRHH para más información.'
            }
        )
        
        
        # Enviar alerta a RRHH
        self._enviar_alerta_rrhh(request.user, survey, score, interpretation)
        
        return Response({
            'success': True,
            'message': 'Encuesta enviada exitosamente',
            'data': {
                'survey_id': survey.id,
                'survey_name': survey.tipo,
                'submission_date': timezone.now().isoformat(),
                'session_id': session_id
            }
        })
    
    def _calculate_score(self, responses):
        """Calcular puntaje de las respuestas"""
        if not responses or len(responses) == 0:
            return 0
        
        total = 0
        for response in responses:
            respuestas = response.get('respuestas', [])
            for val in respuestas:
                total += int(val)
        return total
    
    def _get_interpretation(self, survey_type, score):
        """Interpretar puntaje según tipo de encuesta"""
        if survey_type == 'ansiedad':
            if score <= 7:
                return 'Ansiedad mínima'
            elif score <= 15:
                return 'Ansiedad leve'
            elif score <= 25:
                return 'Ansiedad moderada'
            return 'Ansiedad severa'
        elif survey_type == 'depresion':
            if score <= 9:
                return 'Depresión mínima'
            elif score <= 18:
                return 'Depresión leve'
            elif score <= 29:
                return 'Depresión moderada'
            return 'Depresión severa'
        return 'Sin interpretación disponible'
    
    def _get_nivel_riesgo(self, interpretation):
        """Determinar nivel de riesgo según interpretación"""
        interpretation_lower = interpretation.lower()
        if 'mínima' in interpretation_lower or 'leve' in interpretation_lower:
            return 'bajo'
        elif 'moderada' in interpretation_lower:
            return 'medio'
        elif 'severa' in interpretation_lower:
            return 'alto'
        return 'desconocido'
    
    def _enviar_alerta_rrhh(self, empleado, encuesta, score, interpretacion):
        """Enviar alerta por email a RRHH de forma asíncrona"""
        from django.core.mail import send_mail
        
        email_rrhh = getattr(settings, 'RRHH_EMAIL', 'abner23_08@hotmail.com')
        
        asunto = f"Alerta: Encuesta Completada - {empleado.nombre_completo}"
        cuerpo = f"""<h1>Nueva Encuesta de Salud Mental</h1>
        <p>El empleado <strong>{empleado.nombre_completo}</strong> ha completado la encuesta.</p>
        <ul><li><strong>Tipo:</strong> {encuesta.tipo}</li>
        <li><strong>Nivel de Riesgo:</strong> {interpretacion}</li>
        <li><strong>Puntaje:</strong> {score}</li></ul>
        <p>Favor de revisar el dashboard administrativo para mas detalles.</p>"""
        
        def enviar_async():
            try:
                Notificacion.registrar_alerta(empleado.id, encuesta.id, email_rrhh, asunto, cuerpo, 'enviado', timezone.now())
                logger.info(f"Alerta enviada a RRHH para empleado {empleado.numero_empleado}")
            except Exception as e:
                logger.error(f"Error al enviar alerta: {e}")
        
        threading.Thread(target=enviar_async, daemon=True).start()


# ============== Employee Views ==============

class GetProgressView(APIView):
    """Obtener progreso del empleado en las encuestas"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        id_empleado = request.user.id
        
        # Obtener progreso
        progress = ResultadoEncuestas.objects.filter(
            empleado_id=id_empleado
        ).select_related('encuesta').order_by('-actualizado_en')
        
        if not progress.exists():
            # Crear registros iniciales si no existen
            encuestas_activas = Encuesta.objects.filter(activa=True)
            for encuesta in encuestas_activas:
                ResultadoEncuestas.record_progress(id_empleado, encuesta.id)
            
            return Response({
                'success': True,
                'data': {
                    'id_empleado': id_empleado,
                    'estadisticas': {
                        'total_encuestas': 0,
                        'encuestas_completadas': 0,
                        'en_progreso': 0,
                        'pendientes': 0,
                        'enviadas': 0
                    },
                    'progreso': [],
                    'mensaje': 'No tienes encuestas asignadas actualmente.'
                }
            })
        
        # Mapear resultados
        tipo_nombres = {
            'ansiedad': 'Encuesta de Ansiedad (GAD-7)',
            'depresion': 'Encuesta de Depresión (PHQ-9)',
            'general': 'Encuesta General'
        }
        
        progreso_data = []
        for item in progress:
            encuesta = item.encuesta if hasattr(item, 'encuesta') else None
            encuesta_info = {
                'tipo': encuesta.tipo if encuesta else 'general',
                'descripcion': encuesta.descripcion if encuesta else ''
            }
            
            # Calcular puede_reintentar
            puede_reintentar = False
            if item.estado == 'completada' and item.fecha_completado:
                treinta_dias = timezone.now().date() - timedelta(days=30)
                puede_reintentar = item.fecha_completado < treinta_dias
            
            progreso_data.append({
                'id_encuesta': item.encuesta_id,
                'encuesta_nombre': tipo_nombres.get(encuesta_info['tipo'], 'Encuesta sin nombre'),
                'encuesta_tipo': encuesta_info['tipo'],
                'encuesta_descripcion': encuesta_info['descripcion'],
                'estado': item.estado,
                'iniciado_en': item.iniciado_en,
                'completado_en': item.fecha_completado,
                'enviado_en': item.enviado_en,
                'tiene_puntaje': item.puntaje_total is not None,
                'puede_tomar': item.estado in ['pendiente', 'en_progreso'],
                'puede_reintentar': puede_reintentar
            })
        
        # Calcular estadísticas
        estadisticas = {
            'total_encuestas': progress.count(),
            'encuestas_completadas': progress.filter(estado='completada').count(),
            'en_progreso': progress.filter(estado='en_progreso').count(),
            'pendientes': progress.filter(estado='pendiente').count(),
            'enviadas': progress.filter(estado='enviada').count()
        }
        
        return Response({
            'success': True,
            'data': {
                'id_empleado': id_empleado,
                'estadisticas': estadisticas,
                'progreso': progreso_data,
                'mensaje': f"Tienes {estadisticas['encuestas_completadas']} de {estadisticas['total_encuestas']} encuestas completadas."
            }
        })


# ============== Admin Views ==============

class GetResultsView(APIView):
    """Obtener resultados de encuestas (solo para RRHH)"""
    permission_classes = [APIKeyPermission]

    def get(self, request):
        
        # Obtener parámetros de filtro
        departamento = request.query_params.get('departamento')
        tipo_encuesta = request.query_params.get('tipo_encuesta')
        
        # Construir query
        queryset = ResultadoEncuestas.objects.filter(
            estado='completada'
        ).select_related('empleado', 'encuesta')
        
        if departamento:
            queryset = queryset.filter(empleado__id_departamento=departamento)
        
        if tipo_encuesta:
            queryset = queryset.filter(encuesta__tipo=tipo_encuesta)
        
        # Ordenar y limitar
        results = queryset.order_by('-fecha_completado')[:100]
        
        # Optimización: Obtener todas las respuestas en una sola consulta
        result_ids = [(r.empleado_id, r.encuesta_id) for r in results]
        respuestas_dict = {}
        if result_ids:
            respuestas_query = RespuestasEncuesta.objects.filter(
                empleado_id__in=[r[0] for r in result_ids],
                encuesta_id__in=[r[1] for r in result_ids]
            )
            for resp in respuestas_query:
                respuestas_dict[(resp.empleado_id, resp.encuesta_id)] = resp
        
        # Formatear resultados
        formatted_results = []
        for result in results:
            # Obtener respuestas del diccionario (sin consulta adicional)
            respuestas = respuestas_dict.get((result.empleado_id, result.encuesta_id))
            formatted_results.append({
                'empleado': {
                    'id': result.empleado.id,
                    'nombre': result.empleado.nombre_completo,
                    'departamento': result.empleado.id_departamento
                },
                'encuesta': {
                    'tipo': result.encuesta.tipo,
                    'descripcion': result.encuesta.descripcion
                },
                'detalle_clinico': {
                    'preguntas': respuestas.preguntas if respuestas else [],
                    'respuestas': respuestas.respuestas if respuestas else []
                },
                'puntaje_total': result.puntaje_total,
                'interpretacion': result.interpretacion,
                'nivel_riesgo': result.nivel_riesgo,
                'fecha_completado': result.fecha_completado
            })
        
        # Calcular estadísticas
        total_completed = len(formatted_results)
        average_score = sum(r['puntaje_total'] or 0 for r in formatted_results) / total_completed if total_completed > 0 else 0
        
        distribucion_riesgo = {'bajo': 0, 'medio': 0, 'alto': 0, 'desconocido': 0}
        for r in formatted_results:
            risk = r['nivel_riesgo'] or 'desconocido'
            distribucion_riesgo[risk] = distribucion_riesgo.get(risk, 0) + 1
        
        return Response({
            'success': True,
            'data': {
                'results': formatted_results,
                'statistics': {
                    'total_completed': total_completed,
                    'average_score': average_score,
                    'distribucion_riesgo': distribucion_riesgo
                }
            }
        })


@method_decorator(csrf_exempt, name='dispatch')
class ValidateApiKeyView(View):
    """
    Valida la API Key del administrador.
    Soporta validación via POST (body) o GET (header x-api-key).
    """
    
    def get(self, request):
        """Valida la API Key desde el header x-api-key (para uso en CORS)"""
        # Obtener API Key desde header
        api_key = request.headers.get('x-api-key') or request.GET.get('api_key')
        
        # Obtener la API key desde settings
        admin_api_key = getattr(settings, 'ADMIN_API_KEY', '')
        
        if not api_key:
            return JsonResponse({
                'valid': False,
                'message': 'La API Key es requerida en header x-api-key'
            })
        
        if api_key == admin_api_key:
            return JsonResponse({'valid': True})
        else:
            return JsonResponse({
                'valid': False,
                'message': 'API Key inválida'
            })
    
    def post(self, request):
        try:
            # Obtener el body del request
            data = json.loads(request.body)
            api_key = data.get('apiKey', '')
            
            # Obtener la API key desde settings
            admin_api_key = getattr(settings, 'ADMIN_API_KEY', '')
            
            if not api_key:
                return JsonResponse({
                    'valid': False,
                    'message': 'La API Key es requerida'
                })
            
            if api_key == admin_api_key:
                return JsonResponse({'valid': True})
            else:
                return JsonResponse({
                    'valid': False,
                    'message': 'API Key inválida'
                })
                
        except json.JSONDecodeError:
            return JsonResponse({
                'valid': False,
                'message': 'Error en el formato de la solicitud'
            })


# ============== Empleado CRUD Views ==============

class EmpleadoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para CRUD de empleados (solo admin/RH).
    
    Endpoints:
    - GET /api/empleados - Listar todos los empleados
    - POST /api/empleados - Crear nuevo empleado
    - GET /api/empleados/<id> - Obtener empleado específico
    - PUT /api/empleados/<id> - Actualizar empleado
    - PATCH /api/empleados/<id> - Actualización parcial
    - DELETE /api/empleados/<id> - Eliminar empleado
    """
    queryset = Empleado.objects.all()
    permission_classes = [APIKeyPermission]
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return EmpleadoCreateSerializer
        return EmpleadoSerializer
    
    def get_queryset(self):
        queryset = Empleado.objects.all()
        # Filtrar por parámetros de query
        activo = self.request.query_params.get('activo')
        if activo is not None:
            queryset = queryset.filter(activo=activo.lower() == 'true')
        
        departamento = self.request.query_params.get('departamento')
        if departamento:
            queryset = queryset.filter(id_departamento=departamento)
        
        return queryset
    
    def destroy(self, request, *args, **kwargs):
        """
        Eliminación lógica (soft delete) - marcar activo=False
        """
        instance = self.get_object()
        instance.activo = False
        instance.save()
        return Response(
            {'success': True, 'message': 'Empleado desactivado correctamente'},
            status=status.HTTP_200_OK
        )
    
    def create(self, request, *args, **kwargs):
        """
        Crear nuevo empleado
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            {'success': True, 'message': 'Empleado creado correctamente', 'data': serializer.data},
            status=status.HTTP_201_CREATED
        )
    
    def update(self, request, *args, **kwargs):
        """
        Actualizar empleado
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(
            {'success': True, 'message': 'Empleado actualizado correctamente', 'data': serializer.data}
        )