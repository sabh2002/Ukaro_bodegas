// static/inventory/js/forms.js
// Funciones JavaScript comunes para formularios del sistema de inventario

/**
 * Configuración global
 */
const InventoryForms = {
    config: {
        baseApiUrl: '/api/',
        debounceDelay: 300,
        animationDuration: 300,
        maxRetries: 3
    },
    
    // Cache para resultados de APIs
    cache: new Map(),
    
    // Estado global
    state: {
        currentUser: null,
        csrfToken: null
    }
};

/**
 * Utilidades generales
 */
InventoryForms.utils = {
    
    // Debounce function para optimizar búsquedas
    debounce(func, wait, immediate) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                timeout = null;
                if (!immediate) func(...args);
            };
            const callNow = immediate && !timeout;
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
            if (callNow) func(...args);
        };
    },
    
    // Formatear números con decimales
    formatNumber(number, decimals = 2) {
        return parseFloat(number).toFixed(decimals);
    },
    
    // Formatear precio en bolivianos
    formatPrice(price) {
        return `Bs ${this.formatNumber(price, 2)}`;
    },
    
    // Generar ID único
    generateId(prefix = 'inv') {
        return `${prefix}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    },
    
    // Validar código de barras
    validateBarcode(barcode) {
        // Validación básica: debe ser alfanumérico y tener al menos 4 caracteres
        const regex = /^[a-zA-Z0-9]{4,}$/;
        return regex.test(barcode);
    },
    
    // Sanitizar entrada de texto
    sanitizeInput(input) {
        return input.toString().trim().replace(/[<>]/g, '');
    },
    
    // Obtener token CSRF
    getCsrfToken() {
        if (!this.csrfToken) {
            const tokenElement = document.querySelector('[name=csrfmiddlewaretoken]');
            this.csrfToken = tokenElement ? tokenElement.value : null;
        }
        return this.csrfToken;
    }
};

/**
 * Manejo de APIs
 */
InventoryForms.api = {
    
    // Realizar petición HTTP con manejo de errores
    async request(url, options = {}) {
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': InventoryForms.utils.getCsrfToken(),
                ...options.headers
            },
            credentials: 'same-origin'
        };
        
        const config = { ...defaultOptions, ...options };
        
        try {
            const response = await fetch(url, config);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            return { success: true, data };
            
        } catch (error) {
            console.error('API request failed:', error);
            return { success: false, error: error.message };
        }
    },
    
    // Buscar productos
    async searchProducts(query, filters = {}) {
        const cacheKey = `products_${query}_${JSON.stringify(filters)}`;
        
        if (InventoryForms.cache.has(cacheKey)) {
            return InventoryForms.cache.get(cacheKey);
        }
        
        const params = new URLSearchParams({
            q: query,
            ...filters
        });
        
        const result = await this.request(`${InventoryForms.config.baseApiUrl}products/search/?${params}`);
        
        if (result.success) {
            InventoryForms.cache.set(cacheKey, result);
        }
        
        return result;
    },
    
    // Obtener detalles de producto
    async getProductDetails(productId) {
        const cacheKey = `product_${productId}`;
        
        if (InventoryForms.cache.has(cacheKey)) {
            return InventoryForms.cache.get(cacheKey);
        }
        
        const result = await this.request(`${InventoryForms.config.baseApiUrl}products/${productId}/`);
        
        if (result.success) {
            InventoryForms.cache.set(cacheKey, result);
        }
        
        return result;
    },
    
    // Buscar producto por código de barras
    async getProductByBarcode(barcode) {
        return await this.request(`${InventoryForms.config.baseApiUrl}products/barcode/${barcode}/`);
    },
    
    // Validar código de barras único
    async validateBarcode(barcode, productId = null) {
        const body = { barcode };
        if (productId) body.product_id = productId;
        
        return await this.request(`${InventoryForms.config.baseApiUrl}validate-barcode/`, {
            method: 'POST',
            body: JSON.stringify(body)
        });
    },
    
    // Generar código de barras único
    async generateBarcode() {
        return await this.request(`${InventoryForms.config.baseApiUrl}generate-barcode/`, {
            method: 'POST'
        });
    },
    
    // Obtener categorías
    async getCategories() {
        const cacheKey = 'categories';
        
        if (InventoryForms.cache.has(cacheKey)) {
            return InventoryForms.cache.get(cacheKey);
        }
        
        const result = await this.request(`${InventoryForms.config.baseApiUrl}categories/`);
        
        if (result.success) {
            InventoryForms.cache.set(cacheKey, result);
        }
        
        return result;
    }
};

/**
 * Validación de formularios
 */
InventoryForms.validation = {
    
    // Reglas de validación
    rules: {
        required: (value) => {
            return value !== null && value !== undefined && value.toString().trim() !== '';
        },
        
        minLength: (value, min) => {
            return value.toString().length >= min;
        },
        
        maxLength: (value, max) => {
            return value.toString().length <= max;
        },
        
        numeric: (value) => {
            return !isNaN(value) && !isNaN(parseFloat(value));
        },
        
        positiveNumber: (value) => {
            const num = parseFloat(value);
            return !isNaN(num) && num > 0;
        },
        
        nonNegativeNumber: (value) => {
            const num = parseFloat(value);
            return !isNaN(num) && num >= 0;
        },
        
        barcode: (value) => {
            return InventoryForms.utils.validateBarcode(value);
        },
        
        email: (value) => {
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            return emailRegex.test(value);
        }
    },
    
    // Validar campo individual
    validateField(field, rules) {
        const errors = [];
        const value = field.value;
        
        for (const [ruleName, ruleParams] of Object.entries(rules)) {
            const rule = this.rules[ruleName];
            if (!rule) continue;
            
            let isValid = false;
            if (Array.isArray(ruleParams)) {
                isValid = rule(value, ...ruleParams);
            } else if (ruleParams === true) {
                isValid = rule(value);
            } else {
                isValid = rule(value, ruleParams);
            }
            
            if (!isValid) {
                errors.push(this.getErrorMessage(ruleName, ruleParams));
            }
        }
        
        this.updateFieldUI(field, errors);
        return errors.length === 0;
    },
    
    // Mensajes de error
    getErrorMessage(ruleName, params) {
        const messages = {
            required: 'Este campo es obligatorio',
            minLength: `Debe tener al menos ${params} caracteres`,
            maxLength: `No puede exceder ${params} caracteres`,
            numeric: 'Debe ser un número válido',
            positiveNumber: 'Debe ser un número positivo',
            nonNegativeNumber: 'No puede ser negativo',
            barcode: 'Código de barras inválido',
            email: 'Debe ser un email válido'
        };
        
        return messages[ruleName] || 'Valor inválido';
    },
    
    // Actualizar UI del campo
    updateFieldUI(field, errors) {
        // Remover clases previas
        field.classList.remove('error', 'success');
        
        // Remover mensajes de error previos
        const existingError = field.parentNode.querySelector('.form-error');
        if (existingError) {
            existingError.remove();
        }
        
        if (errors.length > 0) {
            field.classList.add('error');
            
            // Agregar mensaje de error
            const errorDiv = document.createElement('div');
            errorDiv.className = 'form-error';
            errorDiv.innerHTML = `
                <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z"/>
                </svg>
                ${errors[0]}
            `;
            field.parentNode.appendChild(errorDiv);
        } else if (field.value.trim() !== '') {
            field.classList.add('success');
        }
    }
};

/**
 * Componentes de UI
 */
InventoryForms.ui = {
    
    // Mostrar loading en botón
    showButtonLoading(button, text = 'Cargando...') {
        button.disabled = true;
        button.classList.add('loading');
        button.dataset.originalText = button.textContent;
        button.textContent = text;
    },
    
    // Ocultar loading en botón
    hideButtonLoading(button) {
        button.disabled = false;
        button.classList.remove('loading');
        if (button.dataset.originalText) {
            button.textContent = button.dataset.originalText;
            delete button.dataset.originalText;
        }
    },
    
    // Mostrar notificación toast
    showToast(message, type = 'info', duration = 3000) {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `
            <div class="toast-content">
                <span class="toast-message">${message}</span>
                <button class="toast-close">&times;</button>
            </div>
        `;
        
        // Estilos inline para el toast
        Object.assign(toast.style, {
            position: 'fixed',
            top: '20px',
            right: '20px',
            padding: '1rem',
            backgroundColor: type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : '#3b82f6',
            color: 'white',
            borderRadius: '0.5rem',
            boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
            zIndex: '9999',
            opacity: '0',
            transform: 'translateX(100%)',
            transition: 'all 0.3s ease'
        });
        
        document.body.appendChild(toast);
        
        // Animar entrada
        setTimeout(() => {
            toast.style.opacity = '1';
            toast.style.transform = 'translateX(0)';
        }, 10);
        
        // Auto remover
        setTimeout(() => {
            this.removeToast(toast);
        }, duration);
        
        // Botón cerrar
        toast.querySelector('.toast-close').addEventListener('click', () => {
            this.removeToast(toast);
        });
    },
    
    // Remover toast
    removeToast(toast) {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 300);
    },
    
    // Mostrar modal de confirmación
    showConfirmation(message, onConfirm, onCancel = null) {
        const modal = document.createElement('div');
        modal.className = 'confirmation-modal';
        modal.innerHTML = `
            <div class="modal-backdrop">
                <div class="modal-content">
                    <h3>Confirmación</h3>
                    <p>${message}</p>
                    <div class="modal-actions">
                        <button type="button" class="btn btn-secondary" data-action="cancel">Cancelar</button>
                        <button type="button" class="btn btn-primary" data-action="confirm">Confirmar</button>
                    </div>
                </div>
            </div>
        `;
        
        // Estilos inline para el modal
        Object.assign(modal.style, {
            position: 'fixed',
            top: '0',
            left: '0',
            width: '100%',
            height: '100%',
            backgroundColor: 'rgba(0, 0, 0, 0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: '10000'
        });
        
        document.body.appendChild(modal);
        
        // Event listeners
        modal.addEventListener('click', (e) => {
            if (e.target.matches('[data-action="confirm"]')) {
                onConfirm();
                this.removeModal(modal);
            } else if (e.target.matches('[data-action="cancel"]') || e.target === modal) {
                if (onCancel) onCancel();
                this.removeModal(modal);
            }
        });
        
        // ESC key
        const escHandler = (e) => {
            if (e.key === 'Escape') {
                if (onCancel) onCancel();
                this.removeModal(modal);
                document.removeEventListener('keydown', escHandler);
            }
        };
        document.addEventListener('keydown', escHandler);
    },
    
    // Remover modal
    removeModal(modal) {
        if (modal.parentNode) {
            modal.parentNode.removeChild(modal);
        }
    }
};

/**
 * Funcionalidades específicas para formularios de productos
 */
InventoryForms.product = {
    
    // Configurar búsqueda de productos
    setupProductSearch(inputElement, resultsContainer, onSelect) {
        const debouncedSearch = InventoryForms.utils.debounce(async (query) => {
            if (query.length < 2) {
                resultsContainer.innerHTML = '';
                resultsContainer.style.display = 'none';
                return;
            }
            
            const result = await InventoryForms.api.searchProducts(query);
            
            if (result.success && result.data.products) {
                this.displaySearchResults(result.data.products, resultsContainer, onSelect);
            }
        }, InventoryForms.config.debounceDelay);
        
        inputElement.addEventListener('input', (e) => {
            debouncedSearch(e.target.value);
        });
        
        // Ocultar resultados cuando se hace click fuera
        document.addEventListener('click', (e) => {
            if (!inputElement.contains(e.target) && !resultsContainer.contains(e.target)) {
                resultsContainer.style.display = 'none';
            }
        });
    },
    
    // Mostrar resultados de búsqueda
    displaySearchResults(products, container, onSelect) {
        container.innerHTML = '';
        
        if (products.length === 0) {
            container.innerHTML = '<div class="search-no-results">No se encontraron productos</div>';
        } else {
            products.forEach(product => {
                const item = document.createElement('div');
                item.className = 'search-result-item';
                item.innerHTML = `
                    <div class="product-info">
                        <div class="product-name">${product.name}</div>
                        <div class="product-details">
                            <span class="product-barcode">${product.barcode}</span>
                            <span class="product-category">${product.category}</span>
                        </div>
                        <div class="product-price">
                            Stock: ${product.stock} | ${InventoryForms.utils.formatPrice(product.selling_price_bs)}
                        </div>
                    </div>
                `;
                
                item.addEventListener('click', () => {
                    onSelect(product);
                    container.style.display = 'none';
                });
                
                container.appendChild(item);
            });
        }
        
        container.style.display = 'block';
    },
    
    // Calcular margen de ganancia
    calculateMargin(purchasePrice, sellingPrice) {
        const purchase = parseFloat(purchasePrice) || 0;
        const selling = parseFloat(sellingPrice) || 0;
        
        if (purchase === 0) return { amount: 0, percentage: 0 };
        
        const amount = selling - purchase;
        const percentage = (amount / purchase) * 100;
        
        return {
            amount: InventoryForms.utils.formatNumber(amount),
            percentage: InventoryForms.utils.formatNumber(percentage, 1)
        };
    },
    
    // Generar código de barras automático
    async generateBarcode(inputElement) {
        const result = await InventoryForms.api.generateBarcode();
        
        if (result.success && result.data.barcode) {
            inputElement.value = result.data.barcode;
            inputElement.dispatchEvent(new Event('input', { bubbles: true }));
            InventoryForms.ui.showToast('Código de barras generado automáticamente', 'success');
        } else {
            InventoryForms.ui.showToast('Error al generar código de barras', 'error');
        }
    }
};

/**
 * Inicialización
 */
InventoryForms.init = function() {
    // Configurar CSRF token
    this.utils.getCsrfToken();
    
    // Configurar validación automática para todos los formularios
    document.querySelectorAll('form[data-validate="true"]').forEach(form => {
        this.setupFormValidation(form);
    });
    
    // Configurar auto-save para formularios largos
    document.querySelectorAll('form[data-autosave="true"]').forEach(form => {
        this.setupAutoSave(form);
    });
    
    console.log('InventoryForms initialized successfully');
};

// Configurar validación de formulario
InventoryForms.setupFormValidation = function(form) {
    const fields = form.querySelectorAll('[data-validate]');
    
    fields.forEach(field => {
        const rules = JSON.parse(field.dataset.validate);
        
        field.addEventListener('blur', () => {
            this.validation.validateField(field, rules);
        });
        
        field.addEventListener('input', () => {
            if (field.classList.contains('error')) {
                this.validation.validateField(field, rules);
            }
        });
    });
};

// Configurar auto-guardado
InventoryForms.setupAutoSave = function(form) {
    let timeout;
    const delay = 30000; // 30 segundos
    
    form.addEventListener('input', () => {
        clearTimeout(timeout);
        timeout = setTimeout(() => {
            this.autoSaveForm(form);
        }, delay);
    });
};

// Auto-guardar formulario
InventoryForms.autoSaveForm = function(form) {
    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());
    
    // Guardar en localStorage
    const key = `autosave_${form.id || 'form'}_${Date.now()}`;
    localStorage.setItem(key, JSON.stringify(data));
    
    // Limpiar auto-saves antiguos (más de 1 día)
    this.cleanOldAutoSaves();
};

// Limpiar auto-saves antiguos
InventoryForms.cleanOldAutoSaves = function() {
    const oneDayAgo = Date.now() - (24 * 60 * 60 * 1000);
    
    Object.keys(localStorage).forEach(key => {
        if (key.startsWith('autosave_')) {
            const timestamp = parseInt(key.split('_').pop());
            if (timestamp < oneDayAgo) {
                localStorage.removeItem(key);
            }
        }
    });
};

// Inicializar cuando el DOM esté listo
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => InventoryForms.init());
} else {
    InventoryForms.init();
}

// Exportar para uso global
window.InventoryForms = InventoryForms;