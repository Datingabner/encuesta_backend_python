"""
Modelos de la aplicación de Encuestas de Salud Mental
Migrados desde Sequelize (Node.js) a Django ORM
"""
import re
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone


class EmpleadoManager(BaseUserManager):
    """Manager personalizado para el modelo Empleado"""

    def create_user(self, numero_empleado, nombre_completo, password=None, **extra_fields):
        if not numero_empleado:
            raise ValueError('El número de empleado es requerido')
        
        numero_empleado = numero_empleado.strip().upper()
        if not re.match(r'^[A-Z0-9]{4,20}$', numero_empleado):
            raise ValueError('Formato de número de empleado inválido')

        extra_fields.setdefault('email', extra_fields.get('email', '').lower())
        user = self.model(
            numero_empleado=numero_empleado,
            nombre_completo=nombre_completo,
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, numero_empleado, nombre_completo, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        return self.create_user(numero_empleado, nombre_completo, password, **extra_fields)

    def validar_empleado(cls, numero_empleado):
        """Validar empleado por número de empleado (método similar al original)"""
        try:
            return cls.objects.get(
                numero_empleado=numero_empleado.strip().upper(),
                activo=True
            )
        except cls.DoesNotExist:
            return None

cons_creado_en="Creado En"
cons_actual_en="Actualizado En"
class Empleado(AbstractBaseUser, PermissionsMixin):
    """
    Modelo de Empleado
    Equivalente al modelo Sequelize Empleado
    """
    numero_empleado = models.CharField(
        max_length=20, 
        unique=True, 
        db_index=True,
        verbose_name='Número de Empleado'
    )
    nombre_completo = models.CharField(max_length=100, verbose_name='Nombre Completo')
    password = models.CharField(max_length=350)  # Hash de bcrypt
    email = models.EmailField(max_length=100, blank=True, default='')
    id_departamento = models.IntegerField(
        null=True, 
        blank=True, 
        verbose_name='ID Departamento'
    )
    
    activo = models.BooleanField(default=True, verbose_name='Activo')
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    creado_en = models.DateTimeField(auto_now_add=True, verbose_name=cons_creado_en)
    actualizado_en = models.DateTimeField(auto_now=True, verbose_name=cons_actual_en)

    objects = EmpleadoManager()

    USERNAME_FIELD = 'numero_empleado'
    REQUIRED_FIELDS = ['nombre_completo']

    class Meta:
        db_table = 'empleados'
        verbose_name = 'Empleado'
        verbose_name_plural = 'Empleados'
        ordering = ['-creado_en']

    def __str__(self):
        return f"{self.numero_empleado} - {self.nombre_completo}"

    def get_full_name(self):
        return self.nombre_completo

    def get_short_name(self):
        return self.numero_empleado


class Encuesta(models.Model):
    """
    Modelo de Encuesta
    Equivalente al modelo Sequelize Encuesta
    """
    TIPO_CHOICES = [
        ('ansiedad', 'Ansiedad'),
        ('depresion', 'Depresión'),
        ('general', 'General'),
    ]

    tipo = models.CharField(
        max_length=20, 
        choices=TIPO_CHOICES, 
        default='general',
        verbose_name='Tipo de Encuesta'
    )
    descripcion = models.TextField(blank=True, default='', verbose_name='Descripción')
    preguntas = models.JSONField(
        default=list, 
        verbose_name='Preguntas',
        help_text='Array de preguntas en formato JSON'
    )
    activa = models.BooleanField(default=True, verbose_name='Activa')
    creado_en = models.DateTimeField(auto_now_add=True, verbose_name=cons_creado_en)
    actualizado_en = models.DateTimeField(auto_now=True, verbose_name=cons_actual_en)

    class Meta:
        db_table = 'encuestas'
        verbose_name = 'Encuesta'
        verbose_name_plural = 'Encuestas'
        ordering = ['-creado_en']

    def __str__(self):
        return f"{self.get_tipo_display()} - {'Activa' if self.activa else 'Inactiva'}"

    @classmethod
    def get_active_survey(cls, survey_id):
        """Obtener encuesta activa por ID (método equivalente al original)"""
        try:
            return cls.objects.get(id=survey_id, activa=True)
        except cls.DoesNotExist:
            return None


class ResultadoEncuestas(models.Model):
    """
    Modelo de Resultado de Encuestas
    Equivalente al modelo Sequelize ResultadoEncuestas
    """
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('en_progreso', 'En Progreso'),
        ('completada', 'Completada'),
        ('enviada', 'Enviada'),
    ]

    NIVEL_RIESGO_CHOICES = [
        ('bajo', 'Bajo'),
        ('medio', 'Medio'),
        ('alto', 'Alto'),
        ('critico', 'Crítico'),
        ('desconocido', 'Desconocido'),
    ]

    empleado = models.ForeignKey(
        Empleado, 
        on_delete=models.CASCADE, 
        related_name='resultados',
        verbose_name='Empleado'
    )
    encuesta = models.ForeignKey(
        Encuesta, 
        on_delete=models.CASCADE, 
        related_name='resultados',
        verbose_name='Encuesta'
    )
    estado = models.CharField(
        max_length=20, 
        choices=ESTADO_CHOICES, 
        default='pendiente',
        verbose_name='Estado'
    )
    puntaje_total = models.IntegerField(null=True, blank=True, verbose_name='Puntaje Total')
    interpretacion = models.CharField(
        max_length=50, 
        blank=True, 
        default='',
        verbose_name='Interpretación'
    )
    nivel_riesgo = models.CharField(
        max_length=20, 
        choices=NIVEL_RIESGO_CHOICES, 
        default='desconocido',
        verbose_name='Nivel de Riesgo'
    )
    recomendaciones = models.TextField(blank=True, default='', verbose_name='Recomendaciones')
    iniciado_en = models.DateField(null=True, blank=True, verbose_name='Iniciado En')
    fecha_completado = models.DateField(null=True, blank=True, verbose_name='Fecha Completado')
    enviado_en = models.DateTimeField(auto_now_add=True, verbose_name='Enviado En')
    creado_en = models.DateTimeField(auto_now_add=True, verbose_name=cons_creado_en)
    actualizado_en = models.DateTimeField(auto_now=True, verbose_name=cons_actual_en)

    class Meta:
        db_table = 'resultado_encuestas'
        verbose_name = 'Resultado de Encuesta'
        verbose_name_plural = 'Resultados de Encuestas'
        ordering = ['-actualizado_en']
        unique_together = ['empleado', 'encuesta']

    def __str__(self):
        return f"{self.empleado.numero_empleado} - {self.encuesta.tipo} ({self.estado})"

    @classmethod
    def record_progress(cls, employee_id, survey_id, data=None):
        """Registrar progreso del empleado en una encuesta"""
        defaults = {
            'estado': 'en_progreso',
            'iniciado_en': timezone.now().date(),
        }
        if data:
            defaults.update(data)
        
        result, created = cls.objects.get_or_create(
            empleado_id=employee_id,
            encuesta_id=survey_id,
            defaults=defaults
        )
        
        if not created and data:
            for key, value in data.items():
                setattr(result, key, value)
            result.save()
        
        return result

    def mark_as_completed(self, estado='completada', score=None, interpretacion=None, 
                          nivel_riesgo='desconocido', recomendaciones=''):
        """Marcar encuesta como completada"""
        self.estado = estado
        if score is not None:
            self.puntaje_total = score
        if interpretacion:
            self.interpretacion = interpretacion
        if nivel_riesgo:
            self.nivel_riesgo = nivel_riesgo
        if recomendaciones:
            self.recomendaciones = recomendaciones
        self.fecha_completado = timezone.now().date()
        self.save()
        return self


class RespuestasEncuesta(models.Model):
    """
    Modelo de Respuestas de Encuesta
    Equivalente al modelo Sequelize RespuestasEncuesta
    """
    empleado = models.ForeignKey(
        Empleado, 
        on_delete=models.CASCADE, 
        related_name='respuestas',
        verbose_name='Empleado'
    )
    encuesta = models.ForeignKey(
        Encuesta, 
        on_delete=models.CASCADE, 
        related_name='respuestas',
        verbose_name='Encuesta'
    )
    preguntas = models.JSONField(default=list, verbose_name='Preguntas')
    respuestas = models.JSONField(default=list, verbose_name='Respuestas')
    sesion_id = models.CharField(
        max_length=100, 
        blank=True, 
        db_index=True,
        verbose_name='ID de Sesión'
    )
    contestadas_en = models.DateTimeField(
        default=timezone.now, 
        verbose_name='Contestadas En'
    )
    creado_en = models.DateTimeField(auto_now_add=True, verbose_name=cons_creado_en)
    actualizado_en = models.DateTimeField(auto_now=True, verbose_name=cons_actual_en)

    class Meta:
        db_table = 'respuestas_encuesta'
        verbose_name = 'Respuesta de Encuesta'
        verbose_name_plural = 'Respuestas de Encuestas'
        ordering = ['-contestadas_en']
        indexes = [
            models.Index(fields=['empleado', 'encuesta']),
            models.Index(fields=['sesion_id']),
        ]

    def __str__(self):
        return f"Respuesta {self.id} - {self.empleado.numero_empleado}"

    @classmethod
    def save_batch(cls, id_empleado, id_encuesta, responses, session_id):
        """Guardar respuestas en lote"""
        respuesta_records = []
        for response in responses:
            respuesta_records.append(
                cls(
                    empleado_id=id_empleado,
                    encuesta_id=id_encuesta,
                    preguntas=response.get('preguntas', []),
                    respuestas=response.get('respuestas', []),
                    sesion_id=session_id,
                    contestadas_en=timezone.now()
                )
            )
        return cls.objects.bulk_create(respuesta_records)


class Notificacion(models.Model):
    """
    Modelo de Notificación
    Equivalente al modelo Sequelize Notificacion
    """
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('enviado', 'Enviado'),
        ('fallido', 'Fallido'),
    ]

    empleado = models.ForeignKey(
        Empleado, 
        on_delete=models.CASCADE, 
        related_name='notificaciones',
        verbose_name='Empleado'
    )
    encuesta = models.ForeignKey(
        Encuesta, 
        on_delete=models.CASCADE, 
        related_name='notificaciones',
        verbose_name='Encuesta'
    )
    email_destino = models.EmailField(max_length=100, verbose_name='Email Destino')
    asunto = models.CharField(max_length=200, verbose_name='Asunto')
    cuerpo = models.TextField(blank=True, default='', verbose_name='Cuerpo')
    estado = models.CharField(
        max_length=20, 
        choices=ESTADO_CHOICES, 
        default='pendiente',
        verbose_name='Estado'
    )
    enviado_en = models.DateTimeField(null=True, blank=True, verbose_name='Enviado En')
    mensaje_error = models.TextField(blank=True, default='', verbose_name='Mensaje de Error')
    intentos = models.IntegerField(default=0, verbose_name='Intentos')
    creado_en = models.DateTimeField(auto_now_add=True, verbose_name=cons_creado_en)
    actualizado_en = models.DateTimeField(auto_now=True, verbose_name=cons_actual_en)

    class Meta:
        db_table = 'notificaciones'
        verbose_name = 'Notificación'
        verbose_name_plural = 'Notificaciones'
        ordering = ['-creado_en']

    def __str__(self):
        return f"Notificación {self.id} - {self.email_destino} ({self.estado})"

    @classmethod
    def registrar_alerta(cls, id_empleado, id_encuesta, email_rrhh, asunto, cuerpo, 
                        estado='pendiente', enviado_en=None):
        """Registrar una alerta de notificación"""
        return cls.objects.get_or_create(
            empleado_id=id_empleado,
            encuesta_id=id_encuesta,
            defaults={
                'email_destino': email_rrhh,
                'asunto': asunto or 'Sin asunto',
                'cuerpo': cuerpo or '',
                'estado': estado,
                'enviado_en': enviado_en,
                'intentos': 1
            }
        )
