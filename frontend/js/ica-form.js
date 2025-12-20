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
 * ESTRUCTURA DE RENGLONES (según formulario-ICA.md):
 * - Renglón 9: Total ingresos ordinarios
 * - Renglón 10: Total ingresos extraordinarios
 * - Renglón 11: TOTAL INGRESOS (calculado: R9 + R10)
 * - Renglón 12: Devoluciones
 * - Renglón 13: Exportaciones
 * - Renglón 14: Ventas de activos fijos
 * - Renglón 15: Ingresos excluidos
 * - Renglón 16: Ingresos no gravados
 * - Renglón 17: TOTAL INGRESOS GRAVABLES (calculado: R11 - (R12+R13+R14+R15+R16))
 * - Renglón 18: Impuesto de Industria y Comercio
 * - Renglón 19: Avisos y tableros
 * - Renglón 20: Sobretasa
 * - Renglón 21: Total impuesto (calculado: R18 + R19 + R20)
 * - Renglón 22: Descuentos tributarios
 * - Renglón 23: Anticipos del período anterior
 * - Renglón 24: Retenciones sufridas
 * - Renglón 25: Total saldo a pagar
 * - Renglón 26: Total saldo a favor
 */
const ICACalculator = {
    /**
     * Renglón 11: Total ingresos = R9 + R10
     */
    calculateTotalIncome(row9, row10) {
        return (parseFloat(row9) || 0) + (parseFloat(row10) || 0);
    },
    
    /**
     * Renglón 17: Total ingresos gravables
     * Fórmula: R11 - (R12 + R13 + R14 + R15 + R16)
     */
    calculateTaxableIncome(row11, row12, row13, row14, row15, row16) {
        const deductions = 
            (parseFloat(row12) || 0) +
            (parseFloat(row13) || 0) +
            (parseFloat(row14) || 0) +
            (parseFloat(row15) || 0) +
            (parseFloat(row16) || 0);
        return Math.max(0, row11 - deductions);
    },
    
    /**
     * Impuesto por actividad = ingresos * tarifa / 1000
     */
    calculateActivityTax(income, rate) {
        return (parseFloat(income) || 0) * (parseFloat(rate) || 0) / 1000;
    },
    
    /**
     * Renglón 21: Total impuesto = R18 + R19 + R20
     */
    calculateTotalTax(row18, row19, row20) {
        return (parseFloat(row18) || 0) + 
               (parseFloat(row19) || 0) + 
               (parseFloat(row20) || 0);
    },
    
    /**
     * Total créditos = R22 + R23 + R24
     */
    calculateTotalCredits(row22, row23, row24) {
        return (parseFloat(row22) || 0) +
               (parseFloat(row23) || 0) +
               (parseFloat(row24) || 0);
    },
    
    /**
     * Resultado final (Renglones 25 y 26)
     * - Renglón 25: Total saldo a pagar
     * - Renglón 26: Total saldo a favor
     */
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
        const calculableInputs = [
            'row_9', 'row_10', 'row_12', 'row_13', 'row_14', 'row_15', 'row_16',
            'row_19', 'row_20',
            'row_22', 'row_23', 'row_24'
        ];
        
        calculableInputs.forEach(inputId => {
            const input = document.getElementById(inputId);
            if (input) {
                input.addEventListener('input', () => this.recalculate());
                input.addEventListener('blur', () => this.formatCurrency(input));
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
    
    formatCurrency(input) {
        const value = parseFloat(input.value) || 0;
        // Solo formatear visualmente, mantener valor numérico
        input.dataset.rawValue = value;
    }
    
    /**
     * Recalcular todos los campos calculados
     * Actualizado según estructura de renglones del formulario-ICA.md
     */
    recalculate() {
        // Sección C - Ingresos y Base Gravable
        const row9 = this.getValue('row_9');   // Total ingresos ordinarios
        const row10 = this.getValue('row_10'); // Total ingresos extraordinarios
        const row11 = ICACalculator.calculateTotalIncome(row9, row10); // TOTAL INGRESOS
        this.setValue('row_11', row11);
        
        const row12 = this.getValue('row_12'); // Devoluciones
        const row13 = this.getValue('row_13'); // Exportaciones
        const row14 = this.getValue('row_14'); // Ventas de activos fijos
        const row15 = this.getValue('row_15'); // Ingresos excluidos
        const row16 = this.getValue('row_16'); // Ingresos no gravados
        const row17 = ICACalculator.calculateTaxableIncome(row11, row12, row13, row14, row15, row16);
        this.setValue('row_17', row17);
        
        // Sección B - Actividades Gravadas (recalcular impuestos)
        let totalActivitiesTax = 0;
        this.activities.forEach((activity, index) => {
            const tax = ICACalculator.calculateActivityTax(activity.income, activity.tax_rate);
            activity.generated_tax = tax;
            totalActivitiesTax += tax;
            
            const taxElement = document.getElementById(`activity_tax_${index}`);
            if (taxElement) {
                taxElement.textContent = this.formatMoney(tax);
            }
        });
        
        // Actualizar total de actividades en el footer de la tabla
        const totalActivitiesTaxElement = document.getElementById('total-activities-tax');
        if (totalActivitiesTaxElement) {
            totalActivitiesTaxElement.textContent = this.formatMoney(totalActivitiesTax);
        }
        
        // Sección D - Liquidación del Impuesto
        const row18 = totalActivitiesTax; // Impuesto de Industria y Comercio
        this.setValue('row_18', row18);
        
        const row19 = this.getValue('row_19'); // Avisos y tableros
        const row20 = this.getValue('row_20'); // Sobretasa
        const row21 = ICACalculator.calculateTotalTax(row18, row19, row20); // TOTAL IMPUESTO
        this.setValue('row_21', row21);
        
        // Sección E - Descuentos y Anticipos
        const row22 = this.getValue('row_22'); // Descuentos tributarios
        const row23 = this.getValue('row_23'); // Anticipos del período anterior
        const row24 = this.getValue('row_24'); // Retenciones sufridas
        const totalCredits = ICACalculator.calculateTotalCredits(row22, row23, row24);
        this.setValue('total_credits', totalCredits);
        
        // Sección F - Resultado Final (Renglones 25 y 26)
        const result = ICACalculator.calculateResult(row21, totalCredits);
        this.setValue('row_25', result.amountToPay);  // Total saldo a pagar
        this.setValue('row_26', result.balanceInFavor); // Total saldo a favor
        
        // Actualizar visualización
        this.updateResultDisplay(result);
    }
    
    getValue(fieldId) {
        const input = document.getElementById(fieldId);
        return input ? (parseFloat(input.value) || 0) : 0;
    }
    
    setValue(fieldId, value) {
        const input = document.getElementById(fieldId);
        if (input) {
            input.value = value.toFixed(2);
        }
    }
    
    formatMoney(value) {
        return '$' + value.toLocaleString('es-CO', { 
            minimumFractionDigits: 2, 
            maximumFractionDigits: 2 
        });
    }
    
    updateResultDisplay(result) {
        const payContainer = document.getElementById('amount_to_pay_container');
        const favorContainer = document.getElementById('balance_in_favor_container');
        
        if (payContainer && favorContainer) {
            if (result.amountToPay > 0) {
                payContainer.classList.add('highlight');
                favorContainer.classList.remove('highlight');
            } else if (result.balanceInFavor > 0) {
                payContainer.classList.remove('highlight');
                favorContainer.classList.add('highlight');
            }
        }
    }
    
    /**
     * Agregar nueva actividad económica
     */
    addActivity() {
        const activityData = {
            ciiu_code: '',
            description: '',
            income: 0,
            tax_rate: 0,
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
                    <input type="number" class="form-control" 
                           id="activity_income_${index}" 
                           value="${activity.income}"
                           min="0" step="0.01"
                           ${this.isSigned ? 'disabled' : ''}>
                </td>
                <td>
                    <input type="number" class="form-control" 
                           id="activity_rate_${index}" 
                           value="${activity.tax_rate}"
                           min="0" max="100" step="0.01"
                           ${this.isSigned ? 'disabled' : ''}>
                </td>
                <td class="calculated-field" id="activity_tax_${index}">
                    ${this.formatMoney(activity.generated_tax)}
                </td>
                <td>
                    ${!this.isSigned ? `
                        <button type="button" class="btn btn-danger btn-sm" 
                                onclick="formController.removeActivity(${index})">
                            Eliminar
                        </button>
                    ` : ''}
                </td>
            `;
            container.appendChild(row);
            
            // Eventos para recalcular
            const incomeInput = document.getElementById(`activity_income_${index}`);
            const rateInput = document.getElementById(`activity_rate_${index}`);
            
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
            
            // Eventos para actualizar descripción y código
            const ciiuInput = document.getElementById(`activity_ciiu_${index}`);
            const descInput = document.getElementById(`activity_desc_${index}`);
            
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
            
            if (this.declarationId) {
                await DeclarationsAPI.update(this.declarationId, data);
                showAlert('Declaración guardada correctamente', 'success');
            } else {
                const result = await DeclarationsAPI.create({
                    tax_year: parseInt(data.tax_year) || new Date().getFullYear(),
                    declaration_type: data.declaration_type || 'inicial',
                    municipality_id: parseInt(data.municipality_id) || 1
                });
                
                this.declarationId = result.id;
                await DeclarationsAPI.update(this.declarationId, data);
                
                // Actualizar URL
                window.history.pushState({}, '', `?id=${this.declarationId}`);
                showAlert('Declaración creada correctamente', 'success');
            }
            
            hideLoading();
        } catch (error) {
            hideLoading();
            showAlert('Error al guardar: ' + error.message, 'danger');
        }
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
            tax_year: this.getValue('tax_year') || new Date().getFullYear(),
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
            income_base: {
                row_9_ordinary_income: this.getValue('row_9'),
                row_10_extraordinary_income: this.getValue('row_10'),
                row_12_returns: this.getValue('row_12'),
                row_13_exports: this.getValue('row_13'),
                row_14_fixed_assets_sales: this.getValue('row_14'),
                row_15_excluded_income: this.getValue('row_15'),
                row_16_non_taxable_income: this.getValue('row_16')
            },
            activities: this.activities,
            settlement: {
                row_18_ica_tax: this.getValue('row_18'),
                row_19_signs_boards: this.getValue('row_19'),
                row_20_surcharge: this.getValue('row_20')
            },
            discounts: {
                row_22_tax_discounts: this.getValue('row_22'),
                row_23_advance_payments: this.getValue('row_23'),
                row_24_withholdings: this.getValue('row_24')
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
