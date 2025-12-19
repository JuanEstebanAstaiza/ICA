/**
 * Módulo de Formulario ICA
 * Maneja la lógica del formulario de declaración
 * Basado en: Documents/formulario-ICA.md
 */

/**
 * Motor de cálculo del formulario ICA (cliente)
 * Replica las fórmulas del backend para validación doble
 */
const ICACalculator = {
    /**
     * Renglón 10: Total ingresos = R8 + R9
     */
    calculateTotalIncome(row8, row9) {
        return (parseFloat(row8) || 0) + (parseFloat(row9) || 0);
    },
    
    /**
     * Renglón 16: Total ingresos gravables
     * Fórmula: R10 - (R11 + R12 + R13 + R14 + R15)
     */
    calculateTaxableIncome(row10, row11, row12, row13, row14, row15) {
        const deductions = 
            (parseFloat(row11) || 0) +
            (parseFloat(row12) || 0) +
            (parseFloat(row13) || 0) +
            (parseFloat(row14) || 0) +
            (parseFloat(row15) || 0);
        return Math.max(0, row10 - deductions);
    },
    
    /**
     * Impuesto por actividad = ingresos * tarifa / 1000
     */
    calculateActivityTax(income, rate) {
        return (parseFloat(income) || 0) * (parseFloat(rate) || 0) / 1000;
    },
    
    /**
     * Renglón 33: Total impuesto = R30 + R31 + R32
     */
    calculateTotalTax(row30, row31, row32) {
        return (parseFloat(row30) || 0) + 
               (parseFloat(row31) || 0) + 
               (parseFloat(row32) || 0);
    },
    
    /**
     * Total créditos
     */
    calculateTotalCredits(discounts, advances, withholdings) {
        return (parseFloat(discounts) || 0) +
               (parseFloat(advances) || 0) +
               (parseFloat(withholdings) || 0);
    },
    
    /**
     * Resultado final
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
        const calculableInputs = [
            'row_8', 'row_9', 'row_11', 'row_12', 'row_13', 'row_14', 'row_15',
            'row_31', 'row_32',
            'tax_discounts', 'advance_payments', 'withholdings'
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
     */
    recalculate() {
        // Sección B - Base Gravable
        const row8 = this.getValue('row_8');
        const row9 = this.getValue('row_9');
        const row10 = ICACalculator.calculateTotalIncome(row8, row9);
        this.setValue('row_10', row10);
        
        const row11 = this.getValue('row_11');
        const row12 = this.getValue('row_12');
        const row13 = this.getValue('row_13');
        const row14 = this.getValue('row_14');
        const row15 = this.getValue('row_15');
        const row16 = ICACalculator.calculateTaxableIncome(row10, row11, row12, row13, row14, row15);
        this.setValue('row_16', row16);
        
        // Sección C - Actividades (recalcular impuestos)
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
        
        // Sección D - Liquidación
        const row30 = totalActivitiesTax;
        this.setValue('row_30', row30);
        
        const row31 = this.getValue('row_31');
        const row32 = this.getValue('row_32');
        const row33 = ICACalculator.calculateTotalTax(row30, row31, row32);
        this.setValue('row_33', row33);
        
        // Sección E - Créditos
        const discounts = this.getValue('tax_discounts');
        const advances = this.getValue('advance_payments');
        const withholdings = this.getValue('withholdings');
        const totalCredits = ICACalculator.calculateTotalCredits(discounts, advances, withholdings);
        this.setValue('total_credits', totalCredits);
        
        // Sección F - Resultado
        const result = ICACalculator.calculateResult(row33, totalCredits);
        this.setValue('amount_to_pay', result.amountToPay);
        this.setValue('balance_in_favor', result.balanceInFavor);
        
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
        }
        
        // Sección B - Base Gravable
        if (declaration.income_base) {
            const i = declaration.income_base;
            this.setFieldValue('row_8', i.row_8_ordinary_income);
            this.setFieldValue('row_9', i.row_9_extraordinary_income);
            this.setFieldValue('row_11', i.row_11_returns);
            this.setFieldValue('row_12', i.row_12_exports);
            this.setFieldValue('row_13', i.row_13_fixed_assets_sales);
            this.setFieldValue('row_14', i.row_14_excluded_income);
            this.setFieldValue('row_15', i.row_15_non_taxable_income);
        }
        
        // Sección C - Actividades
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
        
        // Sección D - Liquidación
        if (declaration.settlement) {
            const s = declaration.settlement;
            this.setFieldValue('row_31', s.row_31_signs_boards);
            this.setFieldValue('row_32', s.row_32_surcharge);
        }
        
        // Sección E - Descuentos
        if (declaration.discounts) {
            const d = declaration.discounts;
            this.setFieldValue('tax_discounts', d.tax_discounts);
            this.setFieldValue('advance_payments', d.advance_payments);
            this.setFieldValue('withholdings', d.withholdings);
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
            taxpayer: {
                document_type: document.getElementById('document_type')?.value || '',
                document_number: document.getElementById('document_number')?.value || '',
                verification_digit: document.getElementById('verification_digit')?.value || '',
                legal_name: document.getElementById('legal_name')?.value || '',
                address: document.getElementById('address')?.value || '',
                municipality: document.getElementById('taxpayer_municipality')?.value || '',
                department: document.getElementById('taxpayer_department')?.value || '',
                phone: document.getElementById('phone')?.value || '',
                email: document.getElementById('email')?.value || ''
            },
            income_base: {
                row_8_ordinary_income: this.getValue('row_8'),
                row_9_extraordinary_income: this.getValue('row_9'),
                row_11_returns: this.getValue('row_11'),
                row_12_exports: this.getValue('row_12'),
                row_13_fixed_assets_sales: this.getValue('row_13'),
                row_14_excluded_income: this.getValue('row_14'),
                row_15_non_taxable_income: this.getValue('row_15')
            },
            activities: this.activities,
            settlement: {
                row_30_ica_tax: this.getValue('row_30'),
                row_31_signs_boards: this.getValue('row_31'),
                row_32_surcharge: this.getValue('row_32')
            },
            discounts: {
                tax_discounts: this.getValue('tax_discounts'),
                advance_payments: this.getValue('advance_payments'),
                withholdings: this.getValue('withholdings')
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
