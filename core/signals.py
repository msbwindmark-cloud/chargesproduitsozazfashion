from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from .models import Registro, HistorialRegistro

def obtener_datos_texto(instance):
    """Convierte los datos clave del registro en un texto fácil de leer en el admin"""
    if not instance:
        return ""
    # Evitamos fallos si el usuario por algún motivo es Null
    username_creador = instance.usuario.username if instance.usuario else "Desconocido"
    return f"Fecha: {instance.date} | Tipo: {instance.tipo} | Désignation: {instance.designation} | Montant: {instance.montant} MAD | Propietario: {username_creador}"

@receiver(pre_save, sender=Registro)
def auditar_modificacion_previa(sender, instance, **kwargs):
    if instance.pk:
        try:
            registro_antiguo = Registro.objects.get(pk=instance.pk)
            instance._datos_anteriores_texto = obtener_datos_texto(registro_antiguo)
        except Registro.DoesNotExist:
            instance._datos_anteriores_texto = None

@receiver(post_save, sender=Registro)
def auditar_guardado(sender, instance, created, **kwargs):
    # Buscamos el usuario ejecutor que mandamos desde la vista, o usamos el dueño como respaldo
    usuario_accion = getattr(instance, '_usuario_ejecutor', instance.usuario)
    
    if created:
        HistorialRegistro.objects.create(
            usuario=usuario_accion if hasattr(usuario_accion, 'is_authenticated') else None,
            accion='CREAR',
            registro_id=instance.pk,
            datos_anteriores="El registro no existía (Nueva inserción)",
            datos_nuevos=obtener_datos_texto(instance)
        )
    else:
        datos_previos = getattr(instance, '_datos_anteriores_texto', "Datos no capturados")
        HistorialRegistro.objects.create(
            usuario=usuario_accion if hasattr(usuario_accion, 'is_authenticated') else None,
            accion='MODIFICAR',
            registro_id=instance.pk,
            datos_anteriores=datos_previos,
            datos_nuevos=obtener_datos_texto(instance)
        )

@receiver(post_delete, sender=Registro)
def auditar_eliminacion(sender, instance, **kwargs):
    usuario_accion = getattr(instance, '_usuario_ejecutor', instance.usuario)
    
    HistorialRegistro.objects.create(
        usuario=usuario_accion if hasattr(usuario_accion, 'is_authenticated') else None,
        accion='ELIMINAR',
        registro_id=instance.pk,
        datos_anteriores=obtener_datos_texto(instance),
        datos_nuevos="REGISTRO BORRADO DEL SISTEMA"
    )