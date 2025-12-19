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
        
        this.ctx = this.canvas.getContext('2d');
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
        }, 100);
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
        const declarantName = document.getElementById('declarant_name')?.value;
        const declarationDate = document.getElementById('declaration_date')?.value;
        
        if (!declarantName || !declarationDate) {
            showAlert('Por favor complete el nombre del declarante y la fecha', 'warning');
            return;
        }
        
        try {
            showLoading();
            
            const signatureData = {
                declarant_name: declarantName,
                declaration_date: declarationDate,
                accountant_name: document.getElementById('accountant_name')?.value || null,
                professional_card_number: document.getElementById('professional_card')?.value || null,
                signature_image: this.signatureCanvas.toDataURL()
            };
            
            // Llamar a la API para firmar
            if (this.declarationId) {
                await DeclarationsAPI.sign(this.declarationId, signatureData);
                
                showAlert('Declaración firmada correctamente', 'success');
                
                // Callback
                this.onSign(signatureData);
                
                // Cerrar modal
                this.close();
                
                // Recargar página para mostrar estado firmado
                setTimeout(() => {
                    window.location.reload();
                }, 1500);
            } else {
                showAlert('Error: No hay declaración seleccionada', 'danger');
            }
            
            hideLoading();
        } catch (error) {
            hideLoading();
            showAlert('Error al firmar: ' + error.message, 'danger');
        }
    }
}

// Exportar para uso global
window.SignatureCanvas = SignatureCanvas;
window.SignatureModal = SignatureModal;
