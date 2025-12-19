"""
Motor de reglas de cálculo ICA.
Basado en: Documents/formulario-ICA.md
Implementa todas las fórmulas del formulario de manera desacoplada.
"""
from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class IncomeData:
    """Datos de ingresos para cálculo."""
    row_8_ordinary_income: float = 0
    row_9_extraordinary_income: float = 0
    row_11_returns: float = 0
    row_12_exports: float = 0
    row_13_fixed_assets_sales: float = 0
    row_14_excluded_income: float = 0
    row_15_non_taxable_income: float = 0


@dataclass
class ActivityData:
    """Datos de actividad para cálculo."""
    ciiu_code: str
    income: float
    tax_rate: float


@dataclass
class SettlementData:
    """Datos de liquidación para cálculo."""
    row_31_signs_boards: float = 0
    row_32_surcharge: float = 0


@dataclass
class CreditsData:
    """Datos de créditos para cálculo."""
    tax_discounts: float = 0
    advance_payments: float = 0
    withholdings: float = 0


@dataclass
class CalculationResult:
    """Resultado completo del cálculo."""
    # Base gravable
    row_10_total_income: float
    row_16_taxable_income: float
    
    # Actividades
    activities_taxes: List[Dict[str, Any]]
    total_activities_tax: float
    
    # Liquidación
    row_30_ica_tax: float
    row_33_total_tax: float
    
    # Créditos
    total_credits: float
    
    # Resultado final
    amount_to_pay: float
    balance_in_favor: float


class ICACalculationEngine:
    """
    Motor de cálculo para el formulario ICA.
    Implementa las reglas de negocio del documento fuente.
    """
    
    @staticmethod
    def calculate_total_income(data: IncomeData) -> float:
        """
        Renglón 10: Total ingresos.
        Fórmula: R10 = R8 + R9
        """
        return data.row_8_ordinary_income + data.row_9_extraordinary_income
    
    @staticmethod
    def calculate_taxable_income(data: IncomeData) -> float:
        """
        Renglón 16: Total ingresos gravables.
        Fórmula del documento: R16 = R10 - (R11 + R12 + R13 + R14 + R15)
        
        Texto original del Excel:
        "TOTAL INGRESOS GRAVABLES (RENGLÓN 10 MENOS 11,12,13,14 Y 15)"
        """
        total_income = ICACalculationEngine.calculate_total_income(data)
        deductions = (
            data.row_11_returns +
            data.row_12_exports +
            data.row_13_fixed_assets_sales +
            data.row_14_excluded_income +
            data.row_15_non_taxable_income
        )
        return max(0, total_income - deductions)
    
    @staticmethod
    def calculate_activity_tax(activity: ActivityData) -> float:
        """
        Impuesto por actividad.
        Fórmula: impuesto = ingresos * tarifa / 1000
        La tarifa se expresa en por mil.
        """
        return activity.income * activity.tax_rate / 1000
    
    @staticmethod
    def calculate_total_activities_tax(activities: List[ActivityData]) -> tuple:
        """
        Calcula el impuesto total de todas las actividades.
        Renglón 30: Impuesto de Industria y Comercio.
        """
        taxes = []
        total = 0
        
        for activity in activities:
            tax = ICACalculationEngine.calculate_activity_tax(activity)
            taxes.append({
                'ciiu_code': activity.ciiu_code,
                'income': activity.income,
                'tax_rate': activity.tax_rate,
                'generated_tax': tax
            })
            total += tax
        
        return taxes, total
    
    @staticmethod
    def calculate_total_tax(
        ica_tax: float,
        settlement: SettlementData
    ) -> float:
        """
        Renglón 33: Total impuesto.
        Fórmula: R33 = R30 + R31 + R32
        """
        return (
            ica_tax +
            settlement.row_31_signs_boards +
            settlement.row_32_surcharge
        )
    
    @staticmethod
    def calculate_total_credits(credits: CreditsData) -> float:
        """
        Total de créditos y descuentos.
        Sección E del formulario.
        """
        return (
            credits.tax_discounts +
            credits.advance_payments +
            credits.withholdings
        )
    
    @staticmethod
    def calculate_final_result(
        total_tax: float,
        total_credits: float
    ) -> tuple:
        """
        Sección F: Total a Pagar / Saldo a Favor.
        
        Fórmula del documento:
        saldo_a_pagar = total_impuesto - (anticipos + retenciones + descuentos)
        
        Validación: Nunca ambos al mismo tiempo.
        """
        result = total_tax - total_credits
        
        if result > 0:
            return result, 0  # (amount_to_pay, balance_in_favor)
        else:
            return 0, abs(result)  # (amount_to_pay, balance_in_favor)
    
    @classmethod
    def calculate_full_declaration(
        cls,
        income_data: IncomeData,
        activities: List[ActivityData],
        settlement: SettlementData,
        credits: CreditsData
    ) -> CalculationResult:
        """
        Calcula todos los valores del formulario ICA.
        Esta es la función principal del motor de reglas.
        """
        # Base gravable (Sección B)
        row_10 = cls.calculate_total_income(income_data)
        row_16 = cls.calculate_taxable_income(income_data)
        
        # Actividades (Sección C)
        activities_taxes, row_30 = cls.calculate_total_activities_tax(activities)
        
        # Liquidación (Sección D)
        row_33 = cls.calculate_total_tax(row_30, settlement)
        
        # Créditos (Sección E)
        total_credits = cls.calculate_total_credits(credits)
        
        # Resultado (Sección F)
        amount_to_pay, balance_in_favor = cls.calculate_final_result(
            row_33, total_credits
        )
        
        return CalculationResult(
            row_10_total_income=row_10,
            row_16_taxable_income=row_16,
            activities_taxes=activities_taxes,
            total_activities_tax=row_30,
            row_30_ica_tax=row_30,
            row_33_total_tax=row_33,
            total_credits=total_credits,
            amount_to_pay=amount_to_pay,
            balance_in_favor=balance_in_favor
        )


# Instancia global del motor
calculation_engine = ICACalculationEngine()
