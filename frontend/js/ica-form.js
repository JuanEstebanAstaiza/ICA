/**
 * Módulo de Formulario ICA
 * Maneja la lógica del formulario de declaración
 * Basado en: Documents/formulario-ICA.md
 * Actualizado: Diciembre 2024 - Reorganización de renglones según formulario oficial
 */

/**
 * Motor de cálculo del formulario ICA (cliente)
 * Replica las fórmulas del backend para validación doble
 * 
 * ESTRUCTURA DE RENGLONES (según formulario-ICA.md actualizado):
 * 
 * SECCIÓN B - BASE GRAVABLE:
 * - Renglón 8: Total ingresos ordinarios y extraordinarios del período en todo el país
 * - Renglón 9: Menos ingresos fuera del municipio
 * - Renglón 10: Total ingresos ordinarios y extraordinarios en el municipio (R8 - R9)
 * - Renglón 11: Menos ingresos por devoluciones, rebajas y descuentos
 * - Renglón 12: Menos ingresos por exportaciones y venta de activos fijos
 * - Renglón 13: Menos ingresos por actividades excluidas o no sujetas
 * - Renglón 14: Menos ingresos por actividades exentas en el municipio
 * - Renglón 15: Total ingresos gravables (R10 - (R11 + R12 + R13 + R14))
 * 
 * SECCIÓN C - DISCRIMINACIÓN DE INGRESOS:
 * - Renglón 16: Total ingresos gravados en el municipio (suma actividades)
 * - Renglón 17: Total impuesto ICA (suma impuesto por actividades)
 * - Renglón 18: Generación de energía – Capacidad instalada (kW)
 * - Renglón 19: Impuesto Ley 56 de 1981
 * 
 * SECCIÓN D - LIQUIDACIÓN:
 * - Renglón 20: Total impuesto de industria y comercio (R17 + R19)
 * - Renglón 21: Impuesto de avisos y tableros
 * - Renglón 22: Pago por unidades comerciales adicionales del sector financiero
 * - Renglón 23: Sobretasa bomberil
 * - Renglón 24: Sobretasa de seguridad
 * - Renglón 25: Total impuesto a cargo (R20 + R21 + R22 + R23 + R24)
 * - Renglón 26: Menos exenciones o exoneraciones sobre el impuesto
 * - Renglón 27: Menos retenciones practicadas en el municipio
 * - Renglón 28: Menos autorretenciones practicadas en el municipio
 * - Renglón 29: Menos anticipo liquidado en el año anterior
 * - Renglón 30: Anticipo del año siguiente
 * - Renglón 31: Sanciones
 * - Renglón 32: Menos saldo a favor del período anterior
 * - Renglón 33: Total saldo a cargo
 * - Renglón 34: Total saldo a favor
 * 
 * SECCIÓN E - PAGO:
 * - Renglón 35: Valor a pagar
 * - Renglón 36: Descuento por pronto pago
 * - Renglón 37: Intereses de mora
 * - Renglón 38: Total a pagar (R35 - R36 + R37)
 * - Renglón 39: Pago voluntario
 * - Renglón 40: Total a pagar con pago voluntario (R38 + R39)
 */
const ICACalculator = {
    /**
     * Renglón 10: Total ingresos en el municipio = R8 - R9
     */
    calculateTotalIncomeInMunicipality(row8, row9) {
        return Math.max(0, (parseFloat(row8) || 0) - (parseFloat(row9) || 0));
    },
    
    /**
     * Renglón 15: Total ingresos gravables
     * Fórmula: R10 - (R11 + R12 + R13 + R14)
     */
    calculateTaxableIncome(row10, row11, row12, row13, row14) {
        const deductions = 
            (parseFloat(row11) || 0) +
            (parseFloat(row12) || 0) +
            (parseFloat(row13) || 0) +
            (parseFloat(row14) || 0);
        return Math.max(0, (parseFloat(row10) || 0) - deductions);
    },
    
    /**
     * Impuesto por actividad = ingresos * tarifa / 100 (porcentaje)
     */
    calculateActivityTax(income, rate, specialRate = null) {
        const effectiveRate = specialRate !== null ? specialRate : rate;
        return (parseFloat(income) || 0) * (parseFloat(effectiveRate) || 0) / 100;
    },
    
    /**
     * Renglón 19: Impuesto Ley 56 de 1981 = capacidad_kW * tarifa_por_kW
     */
    calculateLaw56Tax(capacityKw, ratePerKw) {
        return (parseFloat(capacityKw) || 0) * (parseFloat(ratePerKw) || 0);
    },
    
    /**
     * Renglón 20: Total impuesto de industria y comercio = R17 + R19
     */
    calculateTotalICATax(row17, row19) {
        return (parseFloat(row17) || 0) + (parseFloat(row19) || 0);
    },
    
    /**
     * Renglón 25: Total impuesto a cargo = R20 + R21 + R22 + R23 + R24
     */
    calculateTotalTaxPayable(row20, row21, row22, row23, row24) {
        return (parseFloat(row20) || 0) + 
               (parseFloat(row21) || 0) + 
               (parseFloat(row22) || 0) +
               (parseFloat(row23) || 0) +
               (parseFloat(row24) || 0);
    },
    
    /**
     * Renglones 33 y 34: Total saldo a cargo / a favor
     * Fórmula: R25 - R26 - R27 - R28 - R29 + R30 + R31 - R32
     */
    calculateFinalBalance(row25, row26, row27, row28, row29, row30, row31, row32) {
        const balance = (parseFloat(row25) || 0) 
            - (parseFloat(row26) || 0)  // exenciones
            - (parseFloat(row27) || 0)  // retenciones municipio
            - (parseFloat(row28) || 0)  // autorretenciones
            - (parseFloat(row29) || 0)  // anticipo año anterior
            + (parseFloat(row30) || 0)  // anticipo año siguiente
            + (parseFloat(row31) || 0)  // sanciones
            - (parseFloat(row32) || 0); // saldo favor anterior
        
        if (balance > 0) {
            return { saldoCargo: balance, saldoFavor: 0 };
        } else {
            return { saldoCargo: 0, saldoFavor: Math.abs(balance) };
        }
    },
    
    /**
     * Renglón 38: Total a pagar = R35 - R36 + R37
     */
    calculateTotalToPay(row35, row36, row37) {
        return Math.max(0, (parseFloat(row35) || 0) - (parseFloat(row36) || 0) + (parseFloat(row37) || 0));
    },
    
    /**
     * Renglón 40: Total a pagar con pago voluntario = R38 + R39
     */
    calculateTotalWithVoluntary(row38, row39) {
        return (parseFloat(row38) || 0) + (parseFloat(row39) || 0);
    },
    
    // ===== Métodos legacy para compatibilidad =====
    calculateTotalIncome(row9, row10) {
        return (parseFloat(row9) || 0) + (parseFloat(row10) || 0);
    },
    
    calculateTotalTax(row18, row19, row20) {
        return (parseFloat(row18) || 0) + 
               (parseFloat(row19) || 0) + 
               (parseFloat(row20) || 0);
    },
    
    calculateTotalCredits(row22, row23, row24) {
        return (parseFloat(row22) || 0) +
               (parseFloat(row23) || 0) +
               (parseFloat(row24) || 0);
    },
    
    calculateResult(totalTax, totalCredits) {
        const result = totalTax - totalCredits;
        if (result > 0) {
            return { amountToPay: result, balanceInFavor: 0 };
        } else {
            return { amountToPay: 0, balanceInFavor: Math.abs(result) };
        }
    }
};

/**
 * Controlador del formulario ICA
 */
class ICAFormController {
    constructor(formElement, declarationId = null) {
        this.form = formElement;
        this.declarationId = declarationId;
        this.activities = [];
        this.isSigned = false;
        
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.setupValidation();
        
        if (this.declarationId) {
            this.loadDeclaration();
        }
    }
    
    bindEvents() {
        // Eventos de cálculo automático en campos editables
        // Actualizado según nueva estructura de renglones (formulario-ICA.md)
        // Sección B - Base Gravable (8-14)
        // Sección C - Energía (18)
        // Sección D - Liquidación (21-32)
        // Sección E - Pago (35-37, 39)
        const editableInputs = [
            'row_8', 'row_9', 'row_11', 'row_12', 'row_13', 'row_14',
            'row_18_energy_kw',
            'row_22', 'row_23', 'row_24', 'row_26', 'row_27', 'row_28', 'row_29', 'row_30', 'row_31', 'row_32',
            'row_36', 'row_37', 'row_39'
        ];
        
        editableInputs.forEach(inputId => {
            const input = document.getElementById(inputId);
            if (input) {
                // Inicializar el valor raw
                input.dataset.rawValue = this.parseFormattedValue(input.value) || 0;
                
                // Recalcular cuando cambia el valor (mientras escribe)
                input.addEventListener('input', (e) => {
                    // Guardar el valor raw mientras escribe (sin formatear)
                    const rawValue = this.parseFormattedValue(e.target.value);
                    e.target.dataset.rawValue = rawValue;
                    this.recalculate();
                });
                
                // Al salir del campo: mostrar con formato visual (separadores de miles)
                input.addEventListener('blur', (e) => {
                    const rawValue = parseFloat(e.target.dataset.rawValue) || 0;
                    e.target.value = this.formatWithSeparators(rawValue);
                });
                
                // Al entrar al campo: mostrar valor numérico puro para editar
                input.addEventListener('focus', (e) => {
                    const rawValue = parseFloat(e.target.dataset.rawValue) || 0;
                    e.target.value = rawValue > 0 ? rawValue.toString() : '';
                    e.target.select();
                });
                
                // Formatear valores iniciales
                const rawValue = parseFloat(input.dataset.rawValue) || 0;
                input.value = this.formatWithSeparators(rawValue);
            }
        });
        
        // Guardar formulario
        this.form.addEventListener('submit', (e) => {
            e.preventDefault();
            this.saveDeclaration();
        });
        
        // Agregar actividad
        const addActivityBtn = document.getElementById('btn-add-activity');
        if (addActivityBtn) {
            addActivityBtn.addEventListener('click', () => this.addActivity());
        }
    }
    
    /**
     * Parsea un valor que puede tener formato colombiano (1.234.567,89) o ser un número simple
     */
    parseFormattedValue(value) {
        if (typeof value === 'number') return value;
        if (!value || value.trim() === '') return 0;
        
        let strValue = value.toString().trim();
        
        // Si tiene punto y coma, es formato colombiano: 1.234.567,89
        if (strValue.includes('.') && strValue.includes(',')) {
            strValue = strValue.replace(/\./g, '').replace(',', '.');
        }
        // Si solo tiene puntos y hay más de uno, son separadores de miles
        else if ((strValue.match(/\./g) || []).length > 1) {
            strValue = strValue.replace(/\./g, '');
        }
        // Si tiene un solo punto con más de 2 dígitos después, es separador de miles
        else if (strValue.includes('.') && !strValue.includes(',')) {
            const parts = strValue.split('.');
            if (parts[1] && parts[1].length > 2) {
                strValue = strValue.replace(/\./g, '');
            }
        }
        // Si tiene coma, la coma es decimal
        else if (strValue.includes(',')) {
            strValue = strValue.replace(',', '.');
        }
        
        return parseFloat(strValue) || 0;
    }
    
    setupValidation() {
        // Validación en tiempo real
        const requiredInputs = this.form.querySelectorAll('[required]');
        requiredInputs.forEach(input => {
            input.addEventListener('blur', () => this.validateField(input));
        });
    }
    
    validateField(input) {
        const value = input.value.trim();
        
        if (input.required && !value) {
            this.showFieldError(input, 'Este campo es obligatorio');
            return false;
        }
        
        if (input.type === 'email' && value) {
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(value)) {
                this.showFieldError(input, 'Ingrese un correo válido');
                return false;
            }
        }
        
        if (input.type === 'number' && value) {
            const num = parseFloat(value);
            if (isNaN(num) || num < 0) {
                this.showFieldError(input, 'Ingrese un valor numérico válido');
                return false;
            }
        }
        
        this.clearFieldError(input);
        return true;
    }
    
    showFieldError(input, message) {
        input.classList.add('is-invalid');
        input.classList.remove('is-valid');
        
        let feedback = input.parentElement.querySelector('.invalid-feedback');
        if (!feedback) {
            feedback = document.createElement('div');
            feedback.className = 'invalid-feedback';
            input.parentElement.appendChild(feedback);
        }
        feedback.textContent = message;
    }
    
    clearFieldError(input) {
        input.classList.remove('is-invalid');
        input.classList.add('is-valid');
        
        const feedback = input.parentElement.querySelector('.invalid-feedback');
        if (feedback) {
            feedback.textContent = '';
        }
    }
    
    /**
     * Formatea un número con separadores de miles (formato colombiano)
     * Solo para visualización, no afecta los cálculos
     * Ejemplo: 1234567 -> "1.234.567"
     * Ejemplo: 1234567.89 -> "1.234.567,89"
     */
    formatWithSeparators(num) {
        if (num === null || num === undefined || isNaN(num)) return '0';
        if (num === 0) return '0';
        
        // Redondear a enteros para evitar problemas con decimales
        const rounded = Math.round(num);
        
        // Separar parte entera
        const integerPart = rounded.toString();
        
        // Agregar separadores de miles (puntos)
        const formattedInteger = integerPart.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
        
        return formattedInteger;
    }
    
    /**
     * Recalcular todos los campos calculados
     * Actualizado según estructura de renglones del formulario-ICA.md
     */
    recalculate() {
        // ===== SECCIÓN B - BASE GRAVABLE =====
        const row8 = this.getValue('row_8');   // Total ingresos en todo el país
        const row9 = this.getValue('row_9');   // Menos ingresos fuera del municipio
        const row10 = ICACalculator.calculateTotalIncomeInMunicipality(row8, row9); // Total en municipio
        this.setValue('row_10', row10);
        
        const row11 = this.getValue('row_11'); // Devoluciones, rebajas y descuentos
        const row12 = this.getValue('row_12'); // Exportaciones y activos fijos
        const row13 = this.getValue('row_13'); // Actividades excluidas
        const row14 = this.getValue('row_14'); // Actividades exentas
        const row15 = ICACalculator.calculateTaxableIncome(row10, row11, row12, row13, row14);
        this.setValue('row_15', row15);
        
        // ===== SECCIÓN C - DISCRIMINACIÓN DE INGRESOS =====
        // Recalcular impuestos de actividades
        let totalActivitiesIncome = 0;
        let totalActivitiesTax = 0;
        this.activities.forEach((activity, index) => {
            const tax = ICACalculator.calculateActivityTax(activity.income, activity.tax_rate, activity.special_rate);
            activity.generated_tax = tax;
            totalActivitiesIncome += parseFloat(activity.income) || 0;
            totalActivitiesTax += tax;
            
            const taxElement = document.getElementById(`activity_tax_${index}`);
            if (taxElement) {
                taxElement.textContent = this.formatMoney(tax);
            }
        });
        
        // Actualizar totales en el footer de la tabla
        const totalTaxedIncomeElement = document.getElementById('total-taxed-income');
        if (totalTaxedIncomeElement) {
            totalTaxedIncomeElement.textContent = this.formatMoney(totalActivitiesIncome);
        }
        const totalActivitiesTaxElement = document.getElementById('total-activities-tax');
        if (totalActivitiesTaxElement) {
            totalActivitiesTaxElement.textContent = this.formatMoney(totalActivitiesTax);
        }
        
        // Renglón 17: Total impuesto ICA (suma de actividades)
        const row17 = totalActivitiesTax;
        
        // Ley 56 de 1981 - Generación de energía
        const row18_energy_kw = this.getValue('row_18_energy_kw');
        // Obtener tarifa por kW de parámetros del municipio (si están disponibles)
        const law56Rate = window.formulaParameters?.ley56_tarifa_kw || 0;
        const row19_law56 = ICACalculator.calculateLaw56Tax(row18_energy_kw, law56Rate);
        this.setValue('row_19_law56', row19_law56);
        
        // ===== SECCIÓN D - LIQUIDACIÓN DEL IMPUESTO =====
        // Renglón 20: Total impuesto de industria y comercio
        const row20 = ICACalculator.calculateTotalICATax(row17, row19_law56);
        this.setValue('row_20', row20);
        
        // Renglones 21-24: Otros impuestos
        const row21 = this.getValue('row_21'); // Avisos y tableros
        const row22 = this.getValue('row_22'); // Unidades comerciales financiero
        const row23 = this.getValue('row_23'); // Sobretasa bomberil
        const row24 = this.getValue('row_24'); // Sobretasa seguridad
        
        // Renglón 25: Total impuesto a cargo
        const row25 = ICACalculator.calculateTotalTaxPayable(row20, row21, row22, row23, row24);
        this.setValue('row_25', row25);
        
        // Renglones 26-32: Deducciones y ajustes
        const row26 = this.getValue('row_26'); // Exenciones
        const row27 = this.getValue('row_27'); // Retenciones municipio
        const row28 = this.getValue('row_28'); // Autorretenciones
        const row29 = this.getValue('row_29'); // Anticipo año anterior
        const row30 = this.getValue('row_30'); // Anticipo año siguiente
        const row31 = this.getValue('row_31'); // Sanciones
        const row32 = this.getValue('row_32'); // Saldo favor anterior
        
        // Renglones 33 y 34: Saldo a cargo / saldo a favor
        const finalBalance = ICACalculator.calculateFinalBalance(row25, row26, row27, row28, row29, row30, row31, row32);
        this.setValue('row_33', finalBalance.saldoCargo);
        this.setValue('row_34', finalBalance.saldoFavor);
        
        // Mostrar indicador visual del resultado
        this.showBalanceIndicator(finalBalance);
        
        // ===== SECCIÓN E - PAGO =====
        // Renglón 35 se autocompleta con el saldo a cargo (lo que debe pagar)
        // Si tiene saldo a favor, no debe pagar nada
        const row35 = finalBalance.saldoCargo; // Autocompletado desde R33
        this.setValue('row_35', row35);
        const row36 = this.getValue('row_36'); // Descuento pronto pago
        const row37 = this.getValue('row_37'); // Intereses mora
        
        // Renglón 38: Total a pagar
        const row38 = ICACalculator.calculateTotalToPay(row35, row36, row37);
        this.setValue('row_38', row38);
        
        // Renglón 39: Pago voluntario
        const row39 = this.getValue('row_39');
        
        // Renglón 40: Total a pagar con pago voluntario
        const row40 = ICACalculator.calculateTotalWithVoluntary(row38, row39);
        this.setValue('row_40', row40);
        
        // Actualizar visualización de resultado
        this.updateResultDisplay({ saldoCargo: finalBalance.saldoCargo, saldoFavor: finalBalance.saldoFavor });
    }
    
    getValue(fieldId) {
        const input = document.getElementById(fieldId);
        if (!input) return 0;
        
        // Si tiene valor raw guardado, usarlo
        if (input.dataset.rawValue !== undefined && input.dataset.rawValue !== '') {
            return parseFloat(input.dataset.rawValue) || 0;
        }
        
        // Si no, parsear el valor formateado
        return this.parseFormattedValue(input.value);
    }
    
    setValue(fieldId, value) {
        const input = document.getElementById(fieldId);
        if (input) {
            const numValue = parseFloat(value) || 0;
            // Guardar valor raw
            input.dataset.rawValue = numValue;
            // Mostrar valor formateado con separadores (solo si no tiene el foco)
            if (document.activeElement !== input) {
                input.value = this.formatWithSeparators(numValue);
            }
        }
    }
    
    formatMoney(value) {
        return '$' + value.toLocaleString('es-CO', { 
            minimumFractionDigits: 2, 
            maximumFractionDigits: 2 
        });
    }
    
    updateResultDisplay(result) {
        // Resaltar el campo que tiene valor (saldo a cargo o saldo a favor)
        const row33Container = document.getElementById('row_33_container');
        const row34Container = document.getElementById('row_34_container');
        
        if (row33Container && row34Container) {
            if (result.saldoCargo > 0) {
                row33Container.style.opacity = '1';
                row33Container.style.transform = 'scale(1.02)';
                row34Container.style.opacity = '0.5';
                row34Container.style.transform = 'scale(1)';
            } else if (result.saldoFavor > 0) {
                row33Container.style.opacity = '0.5';
                row33Container.style.transform = 'scale(1)';
                row34Container.style.opacity = '1';
                row34Container.style.transform = 'scale(1.02)';
            } else {
                row33Container.style.opacity = '1';
                row33Container.style.transform = 'scale(1)';
                row34Container.style.opacity = '1';
                row34Container.style.transform = 'scale(1)';
            }
        }
    }
    
    /**
     * Muestra indicador visual del resultado del balance
     */
    showBalanceIndicator(balance) {
        const indicator = document.getElementById('balance-result-indicator');
        if (!indicator) return;
        
        if (balance.saldoCargo > 0) {
            indicator.style.display = 'block';
            indicator.style.cssText = 'margin-top: 1rem; background: linear-gradient(135deg, #fef2f2, #fee2e2); border-left: 4px solid #dc2626; padding: 1rem;';
            indicator.innerHTML = `
                <strong style="color: #dc2626;">💰 RESULTADO: SALDO A CARGO</strong><br>
                <span style="font-size: 0.875rem;">
                    El contribuyente debe pagar <strong style="color: #dc2626;">$${balance.saldoCargo.toLocaleString('es-CO', {minimumFractionDigits: 2})}</strong> 
                    a la alcaldía. Este valor se traslada automáticamente al Renglón 35.
                </span>
            `;
        } else if (balance.saldoFavor > 0) {
            indicator.style.display = 'block';
            indicator.style.cssText = 'margin-top: 1rem; background: linear-gradient(135deg, #f0fdf4, #dcfce7); border-left: 4px solid #16a34a; padding: 1rem;';
            indicator.innerHTML = `
                <strong style="color: #16a34a;">✅ RESULTADO: SALDO A FAVOR</strong><br>
                <span style="font-size: 0.875rem;">
                    La alcaldía debe al contribuyente <strong style="color: #16a34a;">$${balance.saldoFavor.toLocaleString('es-CO', {minimumFractionDigits: 2})}</strong>.
                    No hay valor a pagar (Renglón 35 = $0).
                </span>
            `;
        } else {
            indicator.style.display = 'block';
            indicator.style.cssText = 'margin-top: 1rem; background: linear-gradient(135deg, #f8fafc, #f1f5f9); border-left: 4px solid #64748b; padding: 1rem;';
            indicator.innerHTML = `
                <strong style="color: #64748b;">⚖️ RESULTADO: BALANCE EN CERO</strong><br>
                <span style="font-size: 0.875rem;">
                    No hay saldo a cargo ni saldo a favor. El contribuyente está al día.
                </span>
            `;
        }
    }
    
    /**
     * Agregar nueva actividad económica
     */
    addActivity() {
        const activityData = {
            activity_type: 'principal',
            ciiu_code: '',
            description: '',
            income: 0,
            tax_rate: 0,
            special_rate: null,
            generated_tax: 0
        };
        
        this.activities.push(activityData);
        this.renderActivities();
    }
    
    removeActivity(index) {
        this.activities.splice(index, 1);
        this.renderActivities();
        this.recalculate();
    }
    
    renderActivities() {
        const container = document.getElementById('activities-container');
        if (!container) return;
        
        container.innerHTML = '';
        
        this.activities.forEach((activity, index) => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>
                    <select class="form-control" 
                            id="activity_type_${index}" 
                            ${this.isSigned ? 'disabled' : ''}>
                        <option value="principal" ${activity.activity_type === 'principal' ? 'selected' : ''}>Principal</option>
                        <option value="secundaria" ${activity.activity_type === 'secundaria' ? 'selected' : ''}>Secundaria</option>
                    </select>
                </td>
                <td>
                    <input type="text" class="form-control" 
                           id="activity_ciiu_${index}" 
                           value="${activity.ciiu_code}"
                           placeholder="Código CIIU"
                           ${this.isSigned ? 'disabled' : ''}>
                </td>
                <td>
                    <input type="text" class="form-control" 
                           id="activity_desc_${index}" 
                           value="${activity.description}"
                           placeholder="Descripción"
                           ${this.isSigned ? 'disabled' : ''}>
                </td>
                <td>
                    <input type="number" class="form-control currency-input" 
                           id="activity_income_${index}" 
                           value="${activity.income}"
                           min="0" step="0.01"
                           ${this.isSigned ? 'disabled' : ''}>
                </td>
                <td>
                    <input type="text" class="form-control" 
                           id="activity_rate_${index}" 
                           value="${activity.tax_rate}"
                           ${this.isSigned ? 'disabled' : ''}>
                </td>
                <td class="calculated-field" id="activity_tax_${index}">
                    ${this.formatMoney(activity.generated_tax)}
                </td>
                <td>
                    <input type="number" class="form-control" 
                           id="activity_special_rate_${index}" 
                           value="${activity.special_rate || ''}"
                           min="0" max="100" step="0.01"
                           placeholder="Esp."
                           title="Tarifa especial (si aplica)"
                           ${this.isSigned ? 'disabled' : ''}>
                </td>
                <td>
                    ${!this.isSigned ? `
                        <button type="button" class="btn btn-danger btn-sm" 
                                onclick="formController.removeActivity(${index})">
                            ✕
                        </button>
                    ` : ''}
                </td>
            `;
            container.appendChild(row);
            
            // Eventos para recalcular
            const incomeInput = document.getElementById(`activity_income_${index}`);
            const rateInput = document.getElementById(`activity_rate_${index}`);
            const specialRateInput = document.getElementById(`activity_special_rate_${index}`);
            
            if (incomeInput) {
                incomeInput.addEventListener('input', (e) => {
                    this.activities[index].income = parseFloat(e.target.value) || 0;
                    this.recalculate();
                });
            }
            
            if (rateInput) {
                rateInput.addEventListener('input', (e) => {
                    this.activities[index].tax_rate = parseFloat(e.target.value) || 0;
                    this.recalculate();
                });
            }
            
            if (specialRateInput) {
                specialRateInput.addEventListener('input', (e) => {
                    const val = e.target.value.trim();
                    this.activities[index].special_rate = val !== '' ? parseFloat(val) : null;
                    this.recalculate();
                });
            }
            
            // Eventos para actualizar tipo, descripción y código
            const typeInput = document.getElementById(`activity_type_${index}`);
            const ciiuInput = document.getElementById(`activity_ciiu_${index}`);
            const descInput = document.getElementById(`activity_desc_${index}`);
            
            if (typeInput) {
                typeInput.addEventListener('change', (e) => {
                    this.activities[index].activity_type = e.target.value;
                });
            }
            
            if (ciiuInput) {
                ciiuInput.addEventListener('input', (e) => {
                    this.activities[index].ciiu_code = e.target.value;
                });
            }
            
            if (descInput) {
                descInput.addEventListener('input', (e) => {
                    this.activities[index].description = e.target.value;
                });
            }
        });
    }
    
    /**
     * Cargar declaración existente
     */
    async loadDeclaration() {
        try {
            showLoading();
            const declaration = await DeclarationsAPI.get(this.declarationId);
            
            this.populateForm(declaration);
            this.isSigned = declaration.is_signed;
            
            if (this.isSigned) {
                this.lockForm();
            }
            
            hideLoading();
        } catch (error) {
            hideLoading();
            showAlert('Error al cargar la declaración: ' + error.message, 'danger');
        }
    }
    
    populateForm(declaration) {
        // Metadatos
        this.setFieldValue('tax_year', declaration.tax_year);
        this.setFieldValue('declaration_type', declaration.declaration_type);
        this.setFieldValue('form_number', declaration.form_number);
        this.setFieldValue('filing_number', declaration.filing_number || 'Se genera al firmar');
        
        // Seleccionar municipio si existe
        if (declaration.municipality_id) {
            const municipalitySelect = document.getElementById('municipality_id');
            if (municipalitySelect) {
                municipalitySelect.value = declaration.municipality_id;
            }
        }
        
        // Sección A - Contribuyente
        if (declaration.taxpayer) {
            const t = declaration.taxpayer;
            this.setFieldValue('document_type', t.document_type);
            this.setFieldValue('document_number', t.document_number);
            this.setFieldValue('verification_digit', t.verification_digit);
            this.setFieldValue('legal_name', t.legal_name);
            this.setFieldValue('address', t.address);
            this.setFieldValue('taxpayer_municipality', t.municipality);
            this.setFieldValue('taxpayer_department', t.department);
            this.setFieldValue('phone', t.phone);
            this.setFieldValue('email', t.email);
            this.setFieldValue('num_establishments', t.num_establishments);
            this.setFieldValue('taxpayer_classification', t.classification);
            this.setFieldValue('is_consortium', t.is_consortium);
            this.setFieldValue('autonomous_patrimony', t.autonomous_patrimony);
        }
        
        // Sección C - Ingresos y Base Gravable (renglones actualizados)
        if (declaration.income_base) {
            const i = declaration.income_base;
            this.setFieldValue('row_9', i.row_9_ordinary_income);
            this.setFieldValue('row_10', i.row_10_extraordinary_income);
            this.setFieldValue('row_12', i.row_12_returns);
            this.setFieldValue('row_13', i.row_13_exports);
            this.setFieldValue('row_14', i.row_14_fixed_assets_sales);
            this.setFieldValue('row_15', i.row_15_excluded_income);
            this.setFieldValue('row_16', i.row_16_non_taxable_income);
        }
        
        // Sección B - Actividades
        if (declaration.activities && declaration.activities.length > 0) {
            this.activities = declaration.activities.map(a => ({
                ciiu_code: a.ciiu_code,
                description: a.description,
                income: a.income,
                tax_rate: a.tax_rate,
                generated_tax: a.generated_tax || 0
            }));
            this.renderActivities();
        }
        
        // Sección D - Liquidación (renglones actualizados)
        if (declaration.settlement) {
            const s = declaration.settlement;
            this.setFieldValue('row_19', s.row_19_signs_boards);
            this.setFieldValue('row_20', s.row_20_surcharge);
        }
        
        // Sección E - Descuentos (renglones actualizados)
        if (declaration.discounts) {
            const d = declaration.discounts;
            this.setFieldValue('row_22', d.row_22_tax_discounts);
            this.setFieldValue('row_23', d.row_23_advance_payments);
            this.setFieldValue('row_24', d.row_24_withholdings);
        }
        
        // Recalcular todos los valores
        this.recalculate();
    }
    
    setFieldValue(fieldId, value) {
        const field = document.getElementById(fieldId);
        if (field && value !== null && value !== undefined) {
            field.value = value;
        }
    }
    
    lockForm() {
        const inputs = this.form.querySelectorAll('input, select, textarea');
        inputs.forEach(input => {
            input.disabled = true;
        });
        
        // Mostrar mensaje de formulario firmado
        const signedBadge = document.createElement('div');
        signedBadge.className = 'alert alert-success';
        signedBadge.innerHTML = '<strong>✅ Formulario Firmado</strong> - Este formulario ha sido firmado y no puede ser modificado.';
        this.form.prepend(signedBadge);
    }
    
    /**
     * Guardar declaración
     */
    async saveDeclaration() {
        if (this.isSigned) {
            showAlert('No se puede modificar un formulario firmado', 'warning');
            return;
        }
        
        // Validar formulario
        if (!this.validateForm()) {
            showAlert('Por favor corrija los errores en el formulario', 'danger');
            return;
        }
        
        try {
            showLoading();
            
            const data = this.collectFormData();
            let isNew = false;
            
            if (this.declarationId) {
                await DeclarationsAPI.update(this.declarationId, data);
            } else {
                isNew = true;
                const result = await DeclarationsAPI.create({
                    tax_year: parseInt(data.tax_year) || new Date().getFullYear(),
                    declaration_type: data.declaration_type || 'inicial',
                    municipality_id: parseInt(data.municipality_id) || 1
                });
                
                this.declarationId = result.id;
                await DeclarationsAPI.update(this.declarationId, data);
                
                // Actualizar URL
                window.history.pushState({}, '', `?id=${this.declarationId}`);
            }
            
            hideLoading();
            
            // Mostrar popup de éxito visible
            this.showSaveSuccessPopup(isNew);
            
        } catch (error) {
            hideLoading();
            showAlert('Error al guardar: ' + error.message, 'danger');
        }
    }
    
    /**
     * Muestra popup de éxito al guardar
     */
    showSaveSuccessPopup(isNew) {
        // Crear overlay
        const overlay = document.createElement('div');
        overlay.id = 'save-success-popup';
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.6);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 10000;
            animation: fadeIn 0.3s ease;
        `;
        
        // Crear popup
        const popup = document.createElement('div');
        popup.style.cssText = `
            background: linear-gradient(135deg, #3b82f6, #1d4ed8);
            color: white;
            padding: 2.5rem;
            border-radius: 1.25rem;
            text-align: center;
            max-width: 420px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
            animation: scaleIn 0.4s ease;
        `;
        
        const title = isNew ? '¡Declaración Creada!' : '¡Declaración Guardada!';
        const message = isNew 
            ? 'Su nueva declaración ha sido creada exitosamente. Ahora puede continuar llenando los campos y firmarla cuando esté lista.'
            : 'Los cambios en su declaración han sido guardados correctamente.';
        const icon = isNew ? '📄' : '💾';
        
        popup.innerHTML = `
            <div style="font-size: 3.5rem; margin-bottom: 1rem;">${icon}</div>
            <h2 style="font-size: 1.5rem; margin-bottom: 0.75rem; font-weight: bold;">${title}</h2>
            <p style="font-size: 0.95rem; opacity: 0.95; margin-bottom: 1.5rem; line-height: 1.5;">
                ${message}
            </p>
            <button id="btn-close-save-popup" style="
                background: white;
                color: #1d4ed8;
                border: none;
                padding: 0.875rem 2rem;
                border-radius: 0.625rem;
                font-size: 1rem;
                font-weight: bold;
                cursor: pointer;
                transition: transform 0.2s;
            ">
                ✓ Entendido
            </button>
        `;
        
        overlay.appendChild(popup);
        document.body.appendChild(overlay);
        
        // Agregar estilos de animación si no existen
        if (!document.getElementById('popup-animations')) {
            const style = document.createElement('style');
            style.id = 'popup-animations';
            style.textContent = `
                @keyframes fadeIn {
                    from { opacity: 0; }
                    to { opacity: 1; }
                }
                @keyframes scaleIn {
                    from { transform: scale(0.8); opacity: 0; }
                    to { transform: scale(1); opacity: 1; }
                }
            `;
            document.head.appendChild(style);
        }
        
        // Cerrar popup
        const closePopup = () => {
            overlay.style.animation = 'fadeIn 0.2s ease reverse';
            setTimeout(() => overlay.remove(), 200);
        };
        
        document.getElementById('btn-close-save-popup').addEventListener('click', closePopup);
        
        // También cerrar con click en overlay
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) closePopup();
        });
        
        // Auto-cerrar después de 4 segundos
        setTimeout(closePopup, 4000);
    }
    
    validateForm() {
        const requiredFields = this.form.querySelectorAll('[required]');
        let isValid = true;
        
        requiredFields.forEach(field => {
            if (!this.validateField(field)) {
                isValid = false;
            }
        });
        
        return isValid;
    }
    
    collectFormData() {
        return {
            tax_year: parseInt(document.getElementById('tax_year')?.value) || new Date().getFullYear(),
            declaration_type: document.getElementById('declaration_type')?.value || 'inicial',
            department: document.getElementById('department')?.value || '',
            bogota_period: document.getElementById('bogota_period')?.value || '',
            corrected_form_number: document.getElementById('corrected_form_number')?.value || '',
            correction_date: document.getElementById('correction_date')?.value || '',
            taxpayer: {
                document_type: document.getElementById('document_type')?.value || '',
                document_number: document.getElementById('document_number')?.value || '',
                verification_digit: document.getElementById('verification_digit')?.value || '',
                legal_name: document.getElementById('legal_name')?.value || '',
                address: document.getElementById('address')?.value || '',
                municipality: document.getElementById('taxpayer_municipality')?.value || '',
                department: document.getElementById('taxpayer_department')?.value || '',
                phone: document.getElementById('phone')?.value || '',
                email: document.getElementById('email')?.value || '',
                num_establishments: parseInt(document.getElementById('num_establishments')?.value) || 1,
                classification: document.getElementById('taxpayer_classification')?.value || '',
                is_consortium: document.getElementById('is_consortium')?.value || 'no',
                autonomous_patrimony: document.getElementById('autonomous_patrimony')?.value || 'no'
            },
            // Sección B - Base Gravable (Renglones 8-15)
            income_base: {
                row_8_total_income_country: this.getValue('row_8'),
                row_9_income_outside_municipality: this.getValue('row_9'),
                row_11_returns_rebates_discounts: this.getValue('row_11'),
                row_12_exports_fixed_assets: this.getValue('row_12'),
                row_13_excluded_non_taxable: this.getValue('row_13'),
                row_14_exempt_income: this.getValue('row_14')
            },
            // Sección C - Actividades
            activities: this.activities,
            // Sección C - Energía (Renglones 18-19)
            energy_generation: {
                installed_capacity_kw: this.getValue('row_18_energy_kw'),
                law_56_tax: this.getValue('row_19_law56')
            },
            // Sección D - Liquidación (Renglones 20-34)
            settlement: {
                row_20_total_ica_tax: this.getValue('row_20'),
                row_21_signs_boards: this.getValue('row_21'),
                row_22_financial_additional_units: this.getValue('row_22'),
                row_23_bomberil_surcharge: this.getValue('row_23'),
                row_24_security_surcharge: this.getValue('row_24'),
                row_26_exemptions: this.getValue('row_26'),
                row_27_withholdings_municipality: this.getValue('row_27'),
                row_28_self_withholdings: this.getValue('row_28'),
                row_29_previous_advance: this.getValue('row_29'),
                row_30_next_year_advance: this.getValue('row_30'),
                row_31_penalties: this.getValue('row_31'),
                row_31_penalty_type: document.getElementById('row_31_type')?.value || '',
                row_32_previous_balance_favor: this.getValue('row_32')
            },
            // Sección E - Pago (Renglones 35-40)
            payment_section: {
                row_35_amount_to_pay: this.getValue('row_35'),
                row_36_early_payment_discount: this.getValue('row_36'),
                row_37_late_interest: this.getValue('row_37'),
                row_39_voluntary_payment: this.getValue('row_39'),
                row_39_voluntary_destination: document.getElementById('row_39_destination')?.value || ''
            }
        };
    }
}

// Funciones auxiliares globales
function showLoading() {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.classList.add('active');
    }
}

function hideLoading() {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.classList.remove('active');
    }
}

function showAlert(message, type = 'info') {
    const alertContainer = document.getElementById('alert-container');
    if (!alertContainer) return;
    
    const alert = document.createElement('div');
    alert.className = `alert alert-${type}`;
    alert.innerHTML = `
        ${message}
        <button type="button" class="modal-close" onclick="this.parentElement.remove()">&times;</button>
    `;
    
    alertContainer.appendChild(alert);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        alert.remove();
    }, 5000);
}

// Variable global para el controlador
let formController = null;

// Exportar para uso global
window.ICACalculator = ICACalculator;
window.ICAFormController = ICAFormController;
window.showLoading = showLoading;
window.hideLoading = hideLoading;
window.showAlert = showAlert;
