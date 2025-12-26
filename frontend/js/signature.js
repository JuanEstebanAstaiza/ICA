/**
 * Módulo de Firma Digital
 * Implementa firma manuscrita mediante Canvas HTML
 * Basado en requerimiento: "Canvas HTML (firma manuscrita)"
 */

class SignatureCanvas {
    constructor(canvasId, options = {}) {
        this.canvas = document.getElementById(canvasId);
        if (!this.canvas) {
            throw new Error(`Canvas element with id '${canvasId}' not found`);
        }
        
        // Usar willReadFrequently para mejor rendimiento
        this.ctx = this.canvas.getContext('2d', { willReadFrequently: true });
        this.isDrawing = false;
        this.lastX = 0;
        this.lastY = 0;
        
        // Opciones de configuración
        this.options = {
            lineWidth: options.lineWidth || 2,
            strokeColor: options.strokeColor || '#000000',
            backgroundColor: options.backgroundColor || '#ffffff',
            ...options
        };
        
        this.init();
    }
    
    init() {
        // Configurar canvas
        this.setCanvasSize();
        this.clear();
        
        // Event listeners para mouse
        this.canvas.addEventListener('mousedown', (e) => this.startDrawing(e));
        this.canvas.addEventListener('mousemove', (e) => this.draw(e));
        this.canvas.addEventListener('mouseup', () => this.stopDrawing());
        this.canvas.addEventListener('mouseout', () => this.stopDrawing());
        
        // Event listeners para touch (dispositivos móviles)
        this.canvas.addEventListener('touchstart', (e) => this.handleTouchStart(e));
        this.canvas.addEventListener('touchmove', (e) => this.handleTouchMove(e));
        this.canvas.addEventListener('touchend', () => this.stopDrawing());
        
        // Resize handler
        window.addEventListener('resize', () => this.handleResize());
    }
    
    setCanvasSize() {
        const parent = this.canvas.parentElement;
        const rect = parent.getBoundingClientRect();
        
        // Mantener ratio de aspecto
        this.canvas.width = rect.width - 40;  // padding
        this.canvas.height = 150;
    }
    
    handleResize() {
        // Guardar imagen actual
        const imageData = this.toDataURL();
        
        // Redimensionar
        this.setCanvasSize();
        
        // Restaurar imagen si había algo
        if (imageData && !this.isEmpty()) {
            const img = new Image();
            img.onload = () => {
                this.ctx.drawImage(img, 0, 0);
            };
            img.src = imageData;
        }
    }
    
    startDrawing(e) {
        this.isDrawing = true;
        const pos = this.getPosition(e);
        this.lastX = pos.x;
        this.lastY = pos.y;
    }
    
    draw(e) {
        if (!this.isDrawing) return;
        
        e.preventDefault();
        
        const pos = this.getPosition(e);
        
        this.ctx.beginPath();
        this.ctx.moveTo(this.lastX, this.lastY);
        this.ctx.lineTo(pos.x, pos.y);
        this.ctx.strokeStyle = this.options.strokeColor;
        this.ctx.lineWidth = this.options.lineWidth;
        this.ctx.lineCap = 'round';
        this.ctx.lineJoin = 'round';
        this.ctx.stroke();
        
        this.lastX = pos.x;
        this.lastY = pos.y;
    }
    
    stopDrawing() {
        this.isDrawing = false;
    }
    
    handleTouchStart(e) {
        e.preventDefault();
        const touch = e.touches[0];
        const mouseEvent = new MouseEvent('mousedown', {
            clientX: touch.clientX,
            clientY: touch.clientY
        });
        this.startDrawing(mouseEvent);
    }
    
    handleTouchMove(e) {
        e.preventDefault();
        const touch = e.touches[0];
        const mouseEvent = new MouseEvent('mousemove', {
            clientX: touch.clientX,
            clientY: touch.clientY
        });
        this.draw(mouseEvent);
    }
    
    getPosition(e) {
        const rect = this.canvas.getBoundingClientRect();
        return {
            x: e.clientX - rect.left,
            y: e.clientY - rect.top
        };
    }
    
    /**
     * Limpiar el canvas
     */
    clear() {
        this.ctx.fillStyle = this.options.backgroundColor;
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
    }
    
    /**
     * Verificar si el canvas está vacío
     */
    isEmpty() {
        const pixelData = this.ctx.getImageData(0, 0, this.canvas.width, this.canvas.height).data;
        
        // Verificar si todos los píxeles son del color de fondo
        const bgColor = this.hexToRgb(this.options.backgroundColor);
        
        for (let i = 0; i < pixelData.length; i += 4) {
            if (pixelData[i] !== bgColor.r || 
                pixelData[i + 1] !== bgColor.g || 
                pixelData[i + 2] !== bgColor.b) {
                return false;
            }
        }
        
        return true;
    }
    
    hexToRgb(hex) {
        const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
        return result ? {
            r: parseInt(result[1], 16),
            g: parseInt(result[2], 16),
            b: parseInt(result[3], 16)
        } : { r: 255, g: 255, b: 255 };
    }
    
    /**
     * Obtener firma como imagen Base64
     */
    toDataURL(type = 'image/png') {
        return this.canvas.toDataURL(type);
    }
    
    /**
     * Obtener firma como Blob
     */
    toBlob(callback, type = 'image/png') {
        this.canvas.toBlob(callback, type);
    }
}

/**
 * Controlador del modal de firma
 */
class SignatureModal {
    constructor(modalId, canvasId, options = {}) {
        this.modal = document.getElementById(modalId);
        this.canvasId = canvasId;
        this.signatureCanvas = null;
        this.accountantCanvas = null;  // Canvas del contador/revisor
        this.onSign = options.onSign || (() => {});
        this.declarationId = options.declarationId;
        
        this.init();
    }
    
    init() {
        // Inicializar canvas cuando se abra el modal
        const openBtn = document.getElementById('btn-open-signature');
        if (openBtn) {
            openBtn.addEventListener('click', () => this.open());
        }
        
        // Botones del modal
        const clearBtn = document.getElementById('btn-clear-signature');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => this.clear());
        }
        
        // Botón limpiar firma contador
        const clearAccountantBtn = document.getElementById('btn-clear-accountant-signature');
        if (clearAccountantBtn) {
            clearAccountantBtn.addEventListener('click', () => this.clearAccountant());
        }
        
        const signBtn = document.getElementById('btn-confirm-signature');
        if (signBtn) {
            signBtn.addEventListener('click', () => this.confirmSignature());
        }
        
        const closeBtn = this.modal?.querySelector('.modal-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.close());
        }
        
        // Cerrar al hacer clic fuera del modal
        if (this.modal) {
            this.modal.addEventListener('click', (e) => {
                if (e.target === this.modal) {
                    this.close();
                }
            });
        }
        
        // Inicializar canvas del contador cuando se seleccione
        const reviewerTypeSelect = document.getElementById('reviewer_type');
        if (reviewerTypeSelect) {
            reviewerTypeSelect.addEventListener('change', () => {
                setTimeout(() => this.initAccountantCanvas(), 150);
            });
        }
    }
    
    open() {
        if (!this.modal) return;
        
        this.modal.classList.add('active');
        
        // Inicializar canvas después de que el modal sea visible
        setTimeout(() => {
            if (!this.signatureCanvas) {
                this.signatureCanvas = new SignatureCanvas(this.canvasId);
            } else {
                this.signatureCanvas.setCanvasSize();
                this.signatureCanvas.clear();
            }
            
            // Inicializar canvas del contador si está visible
            this.initAccountantCanvas();
        }, 100);
    }
    
    initAccountantCanvas() {
        const accountantFields = document.getElementById('accountant-fields');
        const accountantCanvasEl = document.getElementById('accountant-signature-canvas');
        
        if (accountantFields && accountantFields.style.display !== 'none' && accountantCanvasEl) {
            if (!this.accountantCanvas) {
                try {
                    this.accountantCanvas = new SignatureCanvas('accountant-signature-canvas');
                } catch (e) {
                    console.warn('No se pudo inicializar canvas del contador:', e);
                }
            } else {
                this.accountantCanvas.setCanvasSize();
                this.accountantCanvas.clear();
            }
        }
    }
    
    close() {
        if (!this.modal) return;
        this.modal.classList.remove('active');
    }
    
    clear() {
        if (this.signatureCanvas) {
            this.signatureCanvas.clear();
        }
    }
    
    clearAccountant() {
        if (this.accountantCanvas) {
            this.accountantCanvas.clear();
        }
    }
    
    async confirmSignature() {
        if (!this.signatureCanvas) {
            showAlert('Error: Canvas de firma no inicializado', 'danger');
            return;
        }
        
        if (this.signatureCanvas.isEmpty()) {
            showAlert('Por favor, dibuje su firma antes de confirmar', 'warning');
            return;
        }
        
        // Validar campos requeridos
        const declarantName = document.getElementById('declarant_name')?.value?.trim();
        const declarantDocument = document.getElementById('declarant_document')?.value?.trim();
        const declarationDate = document.getElementById('declaration_date')?.value;
        const declarantOath = document.getElementById('declarant_oath')?.checked;
        
        if (!declarantName || !declarantDocument || !declarationDate) {
            showAlert('Por favor complete todos los campos obligatorios del declarante', 'warning');
            return;
        }
        
        if (!declarantOath) {
            showAlert('Debe aceptar la declaración bajo juramento para continuar', 'warning');
            return;
        }
        
        // Verificar si requiere contador/revisor
        const reviewerType = document.getElementById('reviewer_type')?.value || 'none';
        const requiresReviewer = reviewerType !== 'none';
        
        // Validar campos de contador/revisor si aplica
        if (requiresReviewer) {
            const accountantName = document.getElementById('accountant_name')?.value?.trim();
            const accountantDocument = document.getElementById('accountant_document')?.value?.trim();
            const professionalCard = document.getElementById('professional_card')?.value?.trim();
            
            if (!accountantName || !accountantDocument || !professionalCard) {
                showAlert(`Por favor complete todos los campos del ${reviewerType === 'contador' ? 'Contador' : 'Revisor Fiscal'}`, 'warning');
                return;
            }
        }
        
        try {
            showLoading();
            
            // Construir datos de firma según el esquema del backend
            const signatureData = {
                // Datos del declarante
                declarant_name: declarantName,
                declarant_document: declarantDocument,
                declarant_signature_method: document.getElementById('signature_method')?.value || 'manuscrita',
                declarant_oath_accepted: declarantOath,
                declaration_date: declarationDate,
                
                // Datos del contador/revisor fiscal
                requires_fiscal_reviewer: reviewerType === 'revisor_fiscal',
                accountant_name: requiresReviewer ? document.getElementById('accountant_name')?.value?.trim() : null,
                accountant_document: requiresReviewer ? document.getElementById('accountant_document')?.value?.trim() : null,
                accountant_professional_card: requiresReviewer ? document.getElementById('professional_card')?.value?.trim() : null,
                accountant_signature_method: requiresReviewer ? 'manuscrita' : null,
                
                // Imágenes de firma
                signature_image: this.signatureCanvas.toDataURL(),
                accountant_signature_image: null
            };
            
            // Capturar firma del contador/revisor si existe
            if (requiresReviewer && this.accountantCanvas) {
                try {
                    if (!this.accountantCanvas.isEmpty()) {
                        signatureData.accountant_signature_image = this.accountantCanvas.toDataURL();
                    }
                } catch (e) {
                    console.warn('No se pudo capturar firma del contador:', e);
                }
            }
            
            // Llamar a la API para firmar
            if (this.declarationId) {
                const result = await DeclarationsAPI.sign(this.declarationId, signatureData);
                
                // Cerrar modal de firma
                this.close();
                
                // Mostrar popup de éxito muy visible
                this.showSuccessPopup(result);
                
                // Callback
                this.onSign(result);
            } else {
                showAlert('Error: No hay declaración seleccionada', 'danger');
            }
            
            hideLoading();
        } catch (error) {
            hideLoading();
            showAlert('Error al firmar: ' + error.message, 'danger');
        }
    }
    
    /**
     * Muestra un popup de éxito muy visible después de firmar
     */
    showSuccessPopup(result) {
        // Crear overlay
        const overlay = document.createElement('div');
        overlay.id = 'success-popup-overlay';
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.7);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 10000;
            animation: fadeIn 0.3s ease;
        `;
        
        // Crear popup
        const popup = document.createElement('div');
        popup.style.cssText = `
            background: linear-gradient(135deg, #10b981, #059669);
            color: white;
            padding: 3rem;
            border-radius: 1.5rem;
            text-align: center;
            max-width: 500px;
            box-shadow: 0 25px 50px rgba(0, 0, 0, 0.3);
            animation: scaleIn 0.4s ease;
        `;
        
        const filingNumber = result.filing_number || 'Pendiente';
        const signedAt = result.signed_at ? new Date(result.signed_at).toLocaleString() : new Date().toLocaleString();
        
        popup.innerHTML = `
            <div style="font-size: 4rem; margin-bottom: 1rem;">✅</div>
            <h2 style="font-size: 1.75rem; margin-bottom: 1rem; font-weight: bold;">¡Declaración Firmada Exitosamente!</h2>
            <div style="background: rgba(255,255,255,0.2); padding: 1.5rem; border-radius: 1rem; margin: 1.5rem 0;">
                <p style="margin: 0.5rem 0; font-size: 1.1rem;"><strong>📋 Número de Radicado:</strong></p>
                <p style="font-size: 1.5rem; font-weight: bold; font-family: 'Roboto Mono', monospace; margin: 0.5rem 0; background: rgba(0,0,0,0.2); padding: 0.5rem; border-radius: 0.5rem;">${filingNumber}</p>
                <p style="margin: 0.5rem 0; font-size: 0.9rem; opacity: 0.9;">📅 Fecha: ${signedAt}</p>
            </div>
            <p style="font-size: 0.95rem; opacity: 0.9; margin-bottom: 1.5rem;">
                Su declaración ha sido firmada y radicada. Puede descargar el PDF como comprobante.
            </p>
            <button id="btn-close-success-popup" style="
                background: white;
                color: #059669;
                border: none;
                padding: 1rem 2.5rem;
                border-radius: 0.75rem;
                font-size: 1.1rem;
                font-weight: bold;
                cursor: pointer;
                transition: transform 0.2s;
            ">
                Aceptar y Continuar
            </button>
        `;
        
        overlay.appendChild(popup);
        document.body.appendChild(overlay);
        
        // Agregar estilos de animación
        const style = document.createElement('style');
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
        
        // Cerrar popup y recargar
        document.getElementById('btn-close-success-popup').addEventListener('click', () => {
            overlay.remove();
            window.location.reload();
        });
        
        // También cerrar con click en overlay
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                overlay.remove();
                window.location.reload();
            }
        });
    }
}

// Exportar para uso global
window.SignatureCanvas = SignatureCanvas;
window.SignatureModal = SignatureModal;
