from django.utils import timezone


# -------------------------------
# Base Calculator
# -------------------------------
class BaseCalculator:
    def calculate(self, unit, charge_obj):
        """محاسبه مبلغ پایه شارژ هر واحد"""
        raise NotImplementedError

    def calculate_penalty(self, charge_obj, base_total):
        """محاسبه جریمه دیرکرد"""
        if not charge_obj.payment_deadline_date:
            return 0

        check_date = charge_obj.payment_date or timezone.now().date()
        if check_date <= charge_obj.payment_deadline_date:
            return 0

        delay_days = (check_date - charge_obj.payment_deadline_date).days
        penalty_percent = charge_obj.payment_penalty or 0

        return int(base_total * penalty_percent / 100 * delay_days)


# -------------------------------
# 1️⃣ Fixed Charge
# -------------------------------
class FixedChargeCalculator(BaseCalculator):
    def calculate(self, unit, charge_obj):
        return charge_obj.fix_amount or 0


# -------------------------------
# 2️⃣ Area Charge
# -------------------------------
class AreaChargeCalculator(BaseCalculator):
    def calculate(self, unit, charge_obj):
        area = getattr(unit, 'area', 0) or 0
        return area * (charge_obj.area_amount or 0)


# -------------------------------
# 3️⃣ Person Charge
# -------------------------------
class PersonChargeCalculator(BaseCalculator):
    def calculate(self, unit, charge_obj):
        people = getattr(unit, 'people_count', 0) or 0
        return people * (charge_obj.person_amount or 0)


# -------------------------------
# 4️⃣ Fixed Person Charge
# -------------------------------
class FixPersonChargeCalculator(BaseCalculator):
    def calculate(self, unit, charge_obj):
        people = getattr(unit, 'people_count', 0) or 0
        fix = charge_obj.fix_charge_amount or 0
        variable = charge_obj.person_amount or 0
        return fix + (people * variable)


# -------------------------------
# 5️⃣ Fixed Area Charge
# -------------------------------
class FixAreaChargeCalculator(BaseCalculator):
    def calculate(self, unit, charge_obj):
        area = getattr(unit, 'area', 0) or 0
        fix = charge_obj.fix_charge_amount or 0
        variable = charge_obj.area_amount or 0
        return fix + (area * variable)


# -------------------------------
# 6️⃣ Charge by Person + Area
# -------------------------------
class ChargeByPersonAreaCalculator(BaseCalculator):
    def calculate(self, unit, charge_obj):
        area = getattr(unit, 'area', 0) or 0
        people = getattr(unit, 'people_count', 0) or 0
        return (area * (charge_obj.area_amount or 0)) + (people * (charge_obj.person_amount or 0))


# -------------------------------
# 7️⃣ Charge by Fixed Person + Area
# -------------------------------
class ChargeByFixPersonAreaCalculator(BaseCalculator):
    def calculate(self, unit, charge_obj):
        area = getattr(unit, 'area', 0) or 0
        people = getattr(unit, 'people_count', 0) or 0
        fix = charge_obj.fix_charge_amount or 0
        return fix + (area * (charge_obj.area_amount or 0)) + (people * (charge_obj.person_amount or 0))


# -------------------------------
# 8️⃣ Charge Fix + Variable
# -------------------------------
class ChargeFixVariableCalculator(BaseCalculator):
    def calculate(self, unit, charge_obj):
        area = getattr(unit, 'area', 0) or 0
        people = getattr(unit, 'people_count', 0) or 0
        fix = charge_obj.unit_fix_amount or 0
        person_var = charge_obj.unit_variable_person_amount or 0
        area_var = charge_obj.unit_variable_area_amount or 0
        # extra_parking = charge_obj.extra_parking_amount or 0

        return fix + (people * person_var) + (area * area_var)


# -------------------------------
# Mapping charge_type to Calculator
# -------------------------------
CALCULATORS = {
    "fix": FixedChargeCalculator(),
    "area": AreaChargeCalculator(),
    "person": PersonChargeCalculator(),
    "fix_person": FixPersonChargeCalculator(),
    "fix_area": FixAreaChargeCalculator(),
    "person_area": ChargeByPersonAreaCalculator(),
    "fix_person_area": ChargeByFixPersonAreaCalculator(),
    "fix_variable": ChargeFixVariableCalculator(),
}
