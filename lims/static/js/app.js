// جودتي - LIMS JavaScript Functions
// Jawdati Water Quality LIMS Client-side Scripts

// Global Variables
const LIMS = {
    baseUrl: window.location.origin,
    currentUser: null,
    notifications: []
};

// Initialize Application
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
    setupEventListeners();
    loadNotifications();
});

// Initialize Application
function initializeApp() {
    console.log('جودتي LIMS - تم تحميل التطبيق');
    
    // Setup CSRF token for AJAX requests
    const csrfToken = document.querySelector('meta[name="csrf-token"]');
    if (csrfToken) {
        $.ajaxSetup({
            beforeSend: function(xhr, settings) {
                if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
                    xhr.setRequestHeader("X-CSRFToken", csrfToken.getAttribute('content'));
                }
            }
        });
    }
    
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
}

// Setup Event Listeners
function setupEventListeners() {
    // Auto-save forms
    document.querySelectorAll('.auto-save').forEach(form => {
        form.addEventListener('input', debounce(autoSaveForm, 2000));
    });
    
    // Confirm delete actions
    document.querySelectorAll('.confirm-delete').forEach(button => {
        button.addEventListener('click', confirmDelete);
    });
    
    // Sample search
    const sampleSearch = document.getElementById('sample-search');
    if (sampleSearch) {
        sampleSearch.addEventListener('input', debounce(searchSamples, 500));
    }
    
    // Parameter calculation
    document.querySelectorAll('.calculate-parameter').forEach(input => {
        input.addEventListener('input', calculateParameter);
    });
}

// Auto-save Form
function autoSaveForm(event) {
    const form = event.target.closest('form');
    if (!form) return;
    
    const formData = new FormData(form);
    const url = form.getAttribute('data-autosave-url') || form.action;
    
    fetch(url, {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('تم حفظ البيانات تلقائياً', 'success');
        }
    })
    .catch(error => {
        console.error('خطأ في الحفظ التلقائي:', error);
    });
}

// Confirm Delete
function confirmDelete(event) {
    event.preventDefault();
    
    const button = event.target;
    const itemName = button.getAttribute('data-item-name') || 'هذا العنصر';
    
    if (confirm(`هل أنت متأكد من حذف ${itemName}؟\nلا يمكن التراجع عن هذا الإجراء.`)) {
        const form = button.closest('form');
        if (form) {
            form.submit();
        } else {
            window.location.href = button.getAttribute('href');
        }
    }
}

// Search Samples
function searchSamples(event) {
    const query = event.target.value;
    const resultsContainer = document.getElementById('search-results');
    
    if (query.length < 2) {
        resultsContainer.innerHTML = '';
        return;
    }
    
    fetch(`/api/samples/search?q=${encodeURIComponent(query)}`)
        .then(response => response.json())
        .then(data => {
            displaySearchResults(data.samples, resultsContainer);
        })
        .catch(error => {
            console.error('خطأ في البحث:', error);
        });
}

// Display Search Results
function displaySearchResults(samples, container) {
    if (samples.length === 0) {
        container.innerHTML = '<div class="alert alert-info">لم يتم العثور على نتائج</div>';
        return;
    }
    
    const html = samples.map(sample => `
        <div class="card mb-2">
            <div class="card-body">
                <h6 class="card-title">${sample.sample_id}</h6>
                <p class="card-text">
                    <small class="text-muted">
                        النوع: ${sample.sample_type} | 
                        التاريخ: ${formatDate(sample.collection_date)} |
                        الحالة: <span class="badge status-${sample.status}">${sample.status_text}</span>
                    </small>
                </p>
                <a href="/samples/${sample.id}" class="btn btn-sm btn-primary">عرض التفاصيل</a>
            </div>
        </div>
    `).join('');
    
    container.innerHTML = html;
}

// Calculate Parameter
function calculateParameter(event) {
    const input = event.target;
    const parameterId = input.getAttribute('data-parameter-id');
    const value = parseFloat(input.value);
    
    if (isNaN(value)) return;
    
    // Get parameter limits from data attributes
    const minLimit = parseFloat(input.getAttribute('data-min-limit'));
    const maxLimit = parseFloat(input.getAttribute('data-max-limit'));
    
    // Determine conformity
    let conformity = 'conforming';
    if (!isNaN(minLimit) && value < minLimit) conformity = 'non-conforming';
    if (!isNaN(maxLimit) && value > maxLimit) conformity = 'non-conforming';
    
    // Update conformity indicator
    const indicator = document.querySelector(`[data-conformity-for="${parameterId}"]`);
    if (indicator) {
        indicator.className = `badge status-${conformity}`;
        indicator.textContent = conformity === 'conforming' ? 'مطابق' : 'غير مطابق';
    }
    
    // Update input styling
    input.classList.remove('is-valid', 'is-invalid');
    input.classList.add(conformity === 'conforming' ? 'is-valid' : 'is-invalid');
}

// Show Notification
function showNotification(message, type = 'info', duration = 3000) {
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    notification.style.cssText = 'top: 20px; left: 20px; z-index: 9999; min-width: 300px;';
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(notification);
    
    // Auto-remove after duration
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, duration);
}

// Load Notifications
function loadNotifications() {
    fetch('/api/notifications')
        .then(response => response.json())
        .then(data => {
            LIMS.notifications = data.notifications;
            updateNotificationBadge();
        })
        .catch(error => {
            console.error('خطأ في تحميل الإشعارات:', error);
        });
}

// Update Notification Badge
function updateNotificationBadge() {
    const badge = document.getElementById('notification-badge');
    if (badge && LIMS.notifications.length > 0) {
        badge.textContent = LIMS.notifications.length;
        badge.style.display = 'inline';
    }
}

// Format Date
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('ar-DZ', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
}

// Debounce Function
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Export Chart Data
function exportChart(chartId, filename) {
    const chart = document.getElementById(chartId);
    if (!chart) return;
    
    // Implementation for chart export
    console.log(`تصدير الرسم البياني: ${filename}`);
}

// Print Report
function printReport() {
    window.print();
}

// Generate PDF Report
function generatePDFReport(sampleId) {
    showNotification('جاري إنشاء التقرير...', 'info');
    
    fetch(`/api/reports/generate/${sampleId}`, {
        method: 'POST'
    })
    .then(response => response.blob())
    .then(blob => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `تقرير_العينة_${sampleId}.pdf`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        showNotification('تم إنشاء التقرير بنجاح', 'success');
    })
    .catch(error => {
        console.error('خطأ في إنشاء التقرير:', error);
        showNotification('خطأ في إنشاء التقرير', 'danger');
    });
}