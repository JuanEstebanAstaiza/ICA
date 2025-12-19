"""
Tests para el motor de cálculo ICA.
Basado en: Documents/formulario-ICA.md
"""
import pytest
from app.services.calculation_engine import (
    ICACalculationEngine,
    IncomeData,
    ActivityData,
    SettlementData,
    CreditsData
)


class TestICACalculationEngine:
    """Tests para el motor de cálculo del formulario ICA."""
    
    def test_calculate_total_income(self):
        """
        Test Renglón 10: Total ingresos = R8 + R9
        """
        data = IncomeData(
            row_8_ordinary_income=1000000,
            row_9_extraordinary_income=500000
        )
        result = ICACalculationEngine.calculate_total_income(data)
        assert result == 1500000
    
    def test_calculate_taxable_income(self):
        """
        Test Renglón 16: Total ingresos gravables
        Fórmula: R10 - (R11 + R12 + R13 + R14 + R15)
        """
        data = IncomeData(
            row_8_ordinary_income=10000000,
            row_9_extraordinary_income=2000000,
            row_11_returns=500000,
            row_12_exports=1000000,
            row_13_fixed_assets_sales=200000,
            row_14_excluded_income=300000,
            row_15_non_taxable_income=500000
        )
        
        # R10 = 10000000 + 2000000 = 12000000
        # R16 = 12000000 - (500000 + 1000000 + 200000 + 300000 + 500000)
        # R16 = 12000000 - 2500000 = 9500000
        
        result = ICACalculationEngine.calculate_taxable_income(data)
        assert result == 9500000
    
    def test_calculate_taxable_income_no_negative(self):
        """
        Test que el ingreso gravable no sea negativo.
        """
        data = IncomeData(
            row_8_ordinary_income=1000000,
            row_9_extraordinary_income=0,
            row_11_returns=500000,
            row_12_exports=500000,
            row_13_fixed_assets_sales=500000,
            row_14_excluded_income=500000,
            row_15_non_taxable_income=500000
        )
        
        # R10 = 1000000
        # Deducciones = 2500000
        # R16 debería ser max(0, -1500000) = 0
        
        result = ICACalculationEngine.calculate_taxable_income(data)
        assert result == 0
    
    def test_calculate_activity_tax(self):
        """
        Test impuesto por actividad.
        Fórmula: impuesto = ingresos * tarifa / 1000
        """
        activity = ActivityData(
            ciiu_code="G4711",
            income=10000000,
            tax_rate=4.14  # 4.14 por mil
        )
        
        # tax = 10000000 * 4.14 / 1000 = 41400
        result = ICACalculationEngine.calculate_activity_tax(activity)
        assert result == 41400
    
    def test_calculate_total_activities_tax(self):
        """
        Test total impuesto de actividades (Renglón 30).
        """
        activities = [
            ActivityData(ciiu_code="G4711", income=5000000, tax_rate=4.14),
            ActivityData(ciiu_code="I5511", income=3000000, tax_rate=6.0),
        ]
        
        # Act 1: 5000000 * 4.14 / 1000 = 20700
        # Act 2: 3000000 * 6.0 / 1000 = 18000
        # Total = 38700
        
        taxes, total = ICACalculationEngine.calculate_total_activities_tax(activities)
        
        assert len(taxes) == 2
        assert total == 38700
        assert taxes[0]['generated_tax'] == 20700
        assert taxes[1]['generated_tax'] == 18000
    
    def test_calculate_total_tax(self):
        """
        Test Renglón 33: Total impuesto = R30 + R31 + R32
        """
        ica_tax = 100000  # R30
        settlement = SettlementData(
            row_31_signs_boards=15000,  # 15% avisos y tableros
            row_32_surcharge=5000
        )
        
        # R33 = 100000 + 15000 + 5000 = 120000
        result = ICACalculationEngine.calculate_total_tax(ica_tax, settlement)
        assert result == 120000
    
    def test_calculate_total_credits(self):
        """
        Test total de créditos y descuentos.
        """
        credits = CreditsData(
            tax_discounts=10000,
            advance_payments=50000,
            withholdings=20000
        )
        
        result = ICACalculationEngine.calculate_total_credits(credits)
        assert result == 80000
    
    def test_calculate_final_result_amount_to_pay(self):
        """
        Test resultado final: Total a pagar.
        """
        total_tax = 100000
        total_credits = 30000
        
        # Resultado = 100000 - 30000 = 70000 a pagar
        amount_to_pay, balance_in_favor = ICACalculationEngine.calculate_final_result(
            total_tax, total_credits
        )
        
        assert amount_to_pay == 70000
        assert balance_in_favor == 0
    
    def test_calculate_final_result_balance_in_favor(self):
        """
        Test resultado final: Saldo a favor.
        """
        total_tax = 50000
        total_credits = 80000
        
        # Resultado = 50000 - 80000 = -30000 → saldo a favor
        amount_to_pay, balance_in_favor = ICACalculationEngine.calculate_final_result(
            total_tax, total_credits
        )
        
        assert amount_to_pay == 0
        assert balance_in_favor == 30000
    
    def test_calculate_full_declaration(self):
        """
        Test cálculo completo de declaración.
        Caso de uso real basado en Documents/formulario-ICA.md
        """
        income_data = IncomeData(
            row_8_ordinary_income=50000000,
            row_9_extraordinary_income=5000000,
            row_11_returns=2000000,
            row_12_exports=3000000,
            row_13_fixed_assets_sales=1000000,
            row_14_excluded_income=2000000,
            row_15_non_taxable_income=2000000
        )
        
        activities = [
            ActivityData(ciiu_code="G4711", income=25000000, tax_rate=4.14),
            ActivityData(ciiu_code="I5511", income=20000000, tax_rate=6.0),
        ]
        
        settlement = SettlementData(
            row_31_signs_boards=30000,
            row_32_surcharge=10000
        )
        
        credits = CreditsData(
            tax_discounts=20000,
            advance_payments=100000,
            withholdings=50000
        )
        
        result = ICACalculationEngine.calculate_full_declaration(
            income_data, activities, settlement, credits
        )
        
        # Verificaciones
        # R10 = 50000000 + 5000000 = 55000000
        assert result.row_10_total_income == 55000000
        
        # R16 = 55000000 - (2000000 + 3000000 + 1000000 + 2000000 + 2000000) = 45000000
        assert result.row_16_taxable_income == 45000000
        
        # Actividades:
        # Act1: 25000000 * 4.14 / 1000 = 103500
        # Act2: 20000000 * 6.0 / 1000 = 120000
        # Total: 223500
        assert result.row_30_ica_tax == 223500
        
        # R33 = 223500 + 30000 + 10000 = 263500
        assert result.row_33_total_tax == 263500
        
        # Créditos = 20000 + 100000 + 50000 = 170000
        assert result.total_credits == 170000
        
        # Resultado = 263500 - 170000 = 93500 a pagar
        assert result.amount_to_pay == 93500
        assert result.balance_in_favor == 0


class TestValidationRules:
    """Tests para reglas de validación específicas."""
    
    def test_never_both_pay_and_favor(self):
        """
        Validación: Nunca ambos (total a pagar y saldo a favor) al mismo tiempo.
        """
        # Caso 1: A pagar
        pay, favor = ICACalculationEngine.calculate_final_result(100, 50)
        assert not (pay > 0 and favor > 0)
        
        # Caso 2: A favor
        pay, favor = ICACalculationEngine.calculate_final_result(50, 100)
        assert not (pay > 0 and favor > 0)
        
        # Caso 3: Exacto
        pay, favor = ICACalculationEngine.calculate_final_result(100, 100)
        assert pay == 0 and favor == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
