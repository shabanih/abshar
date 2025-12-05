# from django.db.models.signals import post_save, post_delete
# from django.dispatch import receiver
# from .models import (
#     FixedChargeCalc,
#     AreaChargeCalc,
#     PersonChargeCalc,
#     FixPersonChargeCalc,
#     FixAreaChargeCalc,
#     ChargeByPersonAreaCalc,
#     ChargeByFixPersonAreaCalc,
#     ChargeFixVariableCalc,
#     UnifiedCharge
# )
#
# CALC_MODELS = {
#     FixedChargeCalc: 'fixed',
#     AreaChargeCalc: 'area',
#     PersonChargeCalc: 'person',
#     FixPersonChargeCalc: 'fix_person',
#     FixAreaChargeCalc: 'fix_area',
#     ChargeByPersonAreaCalc: 'person_area',
#     ChargeByFixPersonAreaCalc: 'fix_person_area',
#     ChargeFixVariableCalc: 'fix_variable',
# }
#
# def create_or_update_unified_charge(instance, charge_type):
#
#     if not getattr(instance, 'send_notification', False):
#         return  # اگر اطلاع‌رسانی False باشد، ساخت رکورد متوقف می‌شود
#
#     UnifiedCharge.objects.update_or_create(
#         related_object_id=instance.id,
#         related_object_type=charge_type,
#         defaults={
#             'user': getattr(instance, 'user', None),
#             'charge_type': charge_type,
#             'amount': getattr(instance, 'total_charge_month', 0),
#             'description': getattr(instance, 'charge_name', ''),
#             'send_notification_date': getattr(instance, 'send_notification_date', None),
#             'payment_deadline_date': getattr(instance, 'payment_deadline_date', None),
#         }
#     )
#
# def create_signal_for_model(model, charge_type):
#
#     # --- سیگنال ذخیره ---
#     def _save_signal(sender, instance, created, **kwargs):
#         # فقط زمانی رکورد بساز که اطلاع‌رسانی انجام شده باشد
#         if not getattr(instance, 'send_notification', False):
#             return
#
#         create_or_update_unified_charge(instance, charge_type)
#
#     post_save.connect(_save_signal, sender=model, weak=False)
#
#     # --- سیگنال حذف ---
#     def _delete_signal(sender, instance, **kwargs):
#         UnifiedCharge.objects.filter(
#             related_object_type=charge_type,
#             related_object_id=instance.id
#         ).delete()
#
#     post_delete.connect(_delete_signal, sender=model, weak=False)
#
#
# for model, charge_type in CALC_MODELS.items():
#     create_signal_for_model(model, charge_type)
