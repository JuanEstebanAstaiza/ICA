/**
 * API Client para el Sistema ICA
 * Maneja todas las comunicaciones con el backend FastAPI
 */

const API_BASE_URL = '/api/v1';

// Token storage
let accessToken = localStorage.getItem('accessToken');
let refreshToken = localStorage.getItem('refreshToken');

/**
 * Configuración de headers por defecto
 */
function getHeaders() {
    const headers = {
        'Content-Type': 'application/json',
    };
    
    if (accessToken) {
        headers['Authorization'] = `Bearer ${accessToken}`;
    }
    
    return headers;
}

/**
 * Manejo de errores HTTP
 */
async function handleResponse(response) {
    if (response.status === 401) {
        // Intentar refresh token
        const refreshed = await refreshAccessToken();
        if (!refreshed) {
            // Redirigir a login usando constante configurable
            const LOGIN_URL = window.APP_CONFIG?.loginUrl || '/static/templates/login.html';
            window.location.href = LOGIN_URL;
            throw new Error('Sesión expirada');
        }
    }
    
    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Error en la solicitud');
    }
    
    return response.json();
}

/**
 * Refrescar token de acceso
 */
async function refreshAccessToken() {
    if (!refreshToken) return false;
    
    try {
        const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ refresh_token: refreshToken })
        });
        
        if (response.ok) {
            const data = await response.json();
            accessToken = data.access_token;
            refreshToken = data.refresh_token;
            localStorage.setItem('accessToken', accessToken);
            localStorage.setItem('refreshToken', refreshToken);
            return true;
        }
    } catch (error) {
        console.error('Error refreshing token:', error);
    }
    
    return false;
}

// ===================== AUTH API =====================

const AuthAPI = {
    /**
     * Registrar nuevo usuario
     */
    async register(userData) {
        const response = await fetch(`${API_BASE_URL}/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(userData)
        });
        return handleResponse(response);
    },
    
    /**
     * Iniciar sesión
     */
    async login(email, password) {
        const formData = new URLSearchParams();
        formData.append('username', email);
        formData.append('password', password);
        
        const response = await fetch(`${API_BASE_URL}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: formData
        });
        
        const data = await handleResponse(response);
        
        accessToken = data.access_token;
        refreshToken = data.refresh_token;
        localStorage.setItem('accessToken', accessToken);
        localStorage.setItem('refreshToken', refreshToken);
        
        return data;
    },
    
    /**
     * Cerrar sesión
     */
    async logout() {
        try {
            await fetch(`${API_BASE_URL}/auth/logout`, {
                method: 'POST',
                headers: getHeaders()
            });
        } finally {
            accessToken = null;
            refreshToken = null;
            localStorage.removeItem('accessToken');
            localStorage.removeItem('refreshToken');
        }
    },
    
    /**
     * Obtener usuario actual
     */
    async getCurrentUser() {
        const response = await fetch(`${API_BASE_URL}/auth/me`, {
            headers: getHeaders()
        });
        return handleResponse(response);
    },
    
    /**
     * Verificar si está autenticado
     */
    isAuthenticated() {
        return !!accessToken;
    }
};

// ===================== DECLARATIONS API =====================

const DeclarationsAPI = {
    /**
     * Crear nueva declaración
     */
    async create(declarationData) {
        const response = await fetch(`${API_BASE_URL}/declarations/`, {
            method: 'POST',
            headers: getHeaders(),
            body: JSON.stringify(declarationData)
        });
        return handleResponse(response);
    },
    
    /**
     * Listar declaraciones
     */
    async list(filters = {}) {
        const params = new URLSearchParams(filters);
        const response = await fetch(`${API_BASE_URL}/declarations/?${params}`, {
            headers: getHeaders()
        });
        return handleResponse(response);
    },
    
    /**
     * Obtener declaración por ID
     */
    async get(declarationId) {
        const response = await fetch(`${API_BASE_URL}/declarations/${declarationId}`, {
            headers: getHeaders()
        });
        return handleResponse(response);
    },
    
    /**
     * Actualizar declaración
     */
    async update(declarationId, data) {
        const response = await fetch(`${API_BASE_URL}/declarations/${declarationId}`, {
            method: 'PUT',
            headers: getHeaders(),
            body: JSON.stringify(data)
        });
        return handleResponse(response);
    },
    
    /**
     * Calcular valores automáticamente
     */
    async calculate(declarationId) {
        const response = await fetch(`${API_BASE_URL}/declarations/${declarationId}/calculate`, {
            method: 'POST',
            headers: getHeaders()
        });
        return handleResponse(response);
    },
    
    /**
     * Firmar declaración
     */
    async sign(declarationId, signatureData) {
        const response = await fetch(`${API_BASE_URL}/declarations/${declarationId}/sign`, {
            method: 'POST',
            headers: getHeaders(),
            body: JSON.stringify(signatureData)
        });
        return handleResponse(response);
    },
    
    /**
     * Generar PDF
     */
    async generatePDF(declarationId) {
        const response = await fetch(`${API_BASE_URL}/declarations/${declarationId}/generate-pdf`, {
            method: 'POST',
            headers: getHeaders()
        });
        return handleResponse(response);
    },
    
    /**
     * Descargar PDF
     */
    async downloadPDF(declarationId) {
        const response = await fetch(`${API_BASE_URL}/declarations/${declarationId}/download-pdf`, {
            headers: getHeaders()
        });
        
        if (!response.ok) {
            throw new Error('Error al descargar el PDF');
        }
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `declaracion_ica_${declarationId}.pdf`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        a.remove();
    }
};

// ===================== ADMIN API =====================

const AdminAPI = {
    /**
     * Listar municipios
     */
    async listMunicipalities() {
        const response = await fetch(`${API_BASE_URL}/admin/municipalities`, {
            headers: getHeaders()
        });
        return handleResponse(response);
    },
    
    /**
     * Crear municipio
     */
    async createMunicipality(data) {
        const response = await fetch(`${API_BASE_URL}/admin/municipalities`, {
            method: 'POST',
            headers: getHeaders(),
            body: JSON.stringify(data)
        });
        return handleResponse(response);
    },
    
    /**
     * Obtener configuración marca blanca
     */
    async getWhiteLabelConfig(municipalityId) {
        const response = await fetch(`${API_BASE_URL}/admin/white-label/${municipalityId}`, {
            headers: getHeaders()
        });
        return handleResponse(response);
    },
    
    /**
     * Actualizar configuración marca blanca
     */
    async updateWhiteLabelConfig(municipalityId, config) {
        const response = await fetch(`${API_BASE_URL}/admin/white-label/${municipalityId}`, {
            method: 'PUT',
            headers: getHeaders(),
            body: JSON.stringify(config)
        });
        return handleResponse(response);
    },
    
    /**
     * Subir logo
     */
    async uploadLogo(municipalityId, file) {
        const formData = new FormData();
        formData.append('file', file);
        
        const headers = {};
        if (accessToken) {
            headers['Authorization'] = `Bearer ${accessToken}`;
        }
        
        const response = await fetch(`${API_BASE_URL}/admin/white-label/${municipalityId}/logo`, {
            method: 'POST',
            headers: headers,
            body: formData
        });
        return handleResponse(response);
    },
    
    /**
     * Listar actividades económicas
     */
    async listActivities(municipalityId) {
        const response = await fetch(`${API_BASE_URL}/admin/activities/${municipalityId}`, {
            headers: getHeaders()
        });
        return handleResponse(response);
    },
    
    /**
     * Crear actividad económica
     */
    async createActivity(data) {
        const response = await fetch(`${API_BASE_URL}/admin/activities`, {
            method: 'POST',
            headers: getHeaders(),
            body: JSON.stringify(data)
        });
        return handleResponse(response);
    }
};

// Export APIs
window.AuthAPI = AuthAPI;
window.DeclarationsAPI = DeclarationsAPI;
window.AdminAPI = AdminAPI;
