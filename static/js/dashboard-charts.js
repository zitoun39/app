/**
 * dashboard-charts.js
 * مكتبة المخططات البيانية للوحة التحكم
 */

// تكوين الألوان
const chartColors = {
    primary: '#4e73df',
    success: '#1cc88a',
    info: '#36b9cc',
    warning: '#f6c23e',
    danger: '#e74a3b',
    secondary: '#858796',
    light: '#f8f9fc',
    dark: '#5a5c69'
};

// تكوين الخيارات العامة للمخططات
const defaultChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
        legend: {
            position: 'top',
            labels: {
                font: {
                    family: '"Tajawal", "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'
                }
            }
        },
        tooltip: {
            bodyFont: {
                family: '"Tajawal", "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'
            },
            titleFont: {
                family: '"Tajawal", "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'
            }
        }
    },
    scales: {
        x: {
            ticks: {
                font: {
                    family: '"Tajawal", "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'
                }
            }
        },
        y: {
            ticks: {
                font: {
                    family: '"Tajawal", "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'
                }
            }
        }
    }
};

// فئة المخططات البيانية للوحة التحكم
class DashboardCharts {
    constructor() {
        // المخططات
        this.charts = {};
        
        // المتغيرات العامة
        this.currentPeriod = 30;
        
        // تهيئة الأحداث
        this.initEvents();
    }
    
    // تهيئة أحداث الصفحة
    initEvents() {
        // معالجة أحداث تصفية الوقت
        document.querySelectorAll('.time-filter').forEach(button => {
            button.addEventListener('click', (e) => {
                document.querySelectorAll('.time-filter').forEach(btn => btn.classList.remove('active'));
                e.target.classList.add('active');
                this.currentPeriod = parseInt(e.target.dataset.period);
                this.loadAllCharts();
            });
        });
        
        // معالجة حدث تحديث البيانات
        const refreshBtn = document.getElementById('refreshData');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.loadAllCharts());
        }
        
        // معالجة أحداث تغيير نوع الرسم البياني
        document.querySelectorAll('.chart-type').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const chartType = e.target.dataset.type;
                const targetChart = e.target.dataset.target;
                this.updateChartType(targetChart, chartType);
            });
        });
        
        // معالجة أحداث تغيير فئة المعايير
        const paramCategorySelect = document.getElementById('parameterCategory');
        const paramMetricSelect = document.getElementById('parameterMetric');
        const paramLimitSelect = document.getElementById('parameterLimit');
        
        if (paramCategorySelect && paramMetricSelect && paramLimitSelect) {
            paramCategorySelect.addEventListener('change', () => this.loadParametersChart());
            paramMetricSelect.addEventListener('change', () => this.loadParametersChart());
            paramLimitSelect.addEventListener('change', () => this.loadParametersChart());
        }
        
        // معالجة أحداث تحميل البيانات
        document.querySelectorAll('[id^="download"]').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const chartId = e.target.id.replace('download', '');
                this.downloadChartData(chartId);
            });
        });
    }
    
    // تحميل جميع المخططات
    loadAllCharts() {
        // التحقق من وجود عناصر المخططات في الصفحة
        if (document.getElementById('sampleTrendsChart')) {
            this.loadSampleTrendsChart();
        }
        
        if (document.getElementById('sampleStatusChart')) {
            this.loadSampleStatusChart();
        }
        
        if (document.getElementById('conformityChart')) {
            this.loadConformityChart();
        }
        
        if (document.getElementById('regionChart')) {
            this.loadRegionChart();
        }
        
        if (document.getElementById('parametersChart')) {
            this.loadParametersChart();
        }
    }
    
    // تحميل مخطط اتجاهات العينات
    loadSampleTrendsChart() {
        fetch(`/dashboard/api/sample-trends?period=${this.currentPeriod}`)
            .then(response => response.json())
            .then(data => {
                const ctx = document.getElementById('sampleTrendsChart').getContext('2d');
                
                if (this.charts.sampleTrends) {
                    this.charts.sampleTrends.destroy();
                }
                
                this.charts.sampleTrends = new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: data.dates,
                        datasets: [{
                            label: 'عدد العينات',
                            data: data.counts,
                            backgroundColor: chartColors.primary,
                            borderColor: chartColors.primary,
                            tension: 0.1,
                            fill: false
                        }]
                    },
                    options: defaultChartOptions
                });
            })
            .catch(error => console.error('Error loading sample trends chart:', error));
    }
    
    // تحميل مخطط توزيع حالة العينات
    loadSampleStatusChart() {
        fetch(`/dashboard/api/sample-status?period=${this.currentPeriod}`)
            .then(response => response.json())
            .then(data => {
                const ctx = document.getElementById('sampleStatusChart').getContext('2d');
                
                if (this.charts.sampleStatus) {
                    this.charts.sampleStatus.destroy();
                }
                
                this.charts.sampleStatus = new Chart(ctx, {
                    type: 'doughnut',
                    data: {
                        labels: data.labels,
                        datasets: [{
                            data: data.counts,
                            backgroundColor: [
                                chartColors.warning,
                                chartColors.info,
                                chartColors.success,
                                chartColors.primary,
                                chartColors.danger
                            ],
                            borderWidth: 1
                        }]
                    },
                    options: {
                        ...defaultChartOptions,
                        cutout: '50%'
                    }
                });
            })
            .catch(error => console.error('Error loading sample status chart:', error));
    }
    
    // تحميل مخطط نسبة المطابقة للمعايير
    loadConformityChart() {
        fetch(`/dashboard/api/conformity-trends?period=${this.currentPeriod}`)
            .then(response => response.json())
            .then(data => {
                const ctx = document.getElementById('conformityChart').getContext('2d');
                
                if (this.charts.conformity) {
                    this.charts.conformity.destroy();
                }
                
                this.charts.conformity = new Chart(ctx, {
                    type: 'bar',
                    data: {
                        labels: data.dates,
                        datasets: [{
                            label: 'نسبة المطابقة (%)',
                            data: data.rates,
                            backgroundColor: data.rates.map(rate => 
                                rate >= 90 ? chartColors.success : 
                                rate >= 75 ? chartColors.info : 
                                rate >= 50 ? chartColors.warning : chartColors.danger
                            ),
                            borderWidth: 1
                        }]
                    },
                    options: {
                        ...defaultChartOptions,
                        scales: {
                            ...defaultChartOptions.scales,
                            y: {
                                ...defaultChartOptions.scales.y,
                                min: 0,
                                max: 100
                            }
                        }
                    }
                });
            })
            .catch(error => console.error('Error loading conformity chart:', error));
    }
    
    // تحميل مخطط توزيع العينات حسب المنطقة
    loadRegionChart() {
        fetch(`/dashboard/api/region-distribution?period=${this.currentPeriod}`)
            .then(response => response.json())
            .then(data => {
                const ctx = document.getElementById('regionChart').getContext('2d');
                
                if (this.charts.region) {
                    this.charts.region.destroy();
                }
                
                // إنشاء مصفوفة ألوان بناءً على عدد المناطق
                const backgroundColors = [];
                const colorPalette = [chartColors.primary, chartColors.success, chartColors.info, 
                                     chartColors.warning, chartColors.danger, chartColors.secondary];
                
                for (let i = 0; i < data.regions.length; i++) {
                    backgroundColors.push(colorPalette[i % colorPalette.length]);
                }
                
                this.charts.region = new Chart(ctx, {
                    type: 'bar',
                    data: {
                        labels: data.regions,
                        datasets: [{
                            label: 'عدد العينات',
                            data: data.counts,
                            backgroundColor: backgroundColors,
                            borderWidth: 1
                        }]
                    },
                    options: defaultChartOptions
                });
            })
            .catch(error => console.error('Error loading region chart:', error));
    }
    
    // تحميل مخطط تحليل المعايير
    loadParametersChart() {
        const category = document.getElementById('parameterCategory').value;
        const metric = document.getElementById('parameterMetric').value;
        const limit = document.getElementById('parameterLimit').value;
        
        fetch(`/dashboard/api/parameter-analysis?period=${this.currentPeriod}&category=${category}&metric=${metric}&limit=${limit}`)
            .then(response => response.json())
            .then(data => {
                const ctx = document.getElementById('parametersChart').getContext('2d');
                
                if (this.charts.parameters) {
                    this.charts.parameters.destroy();
                }
                
                // تحديد نوع المخطط بناءً على البيانات
                const chartType = data.parameters.length > 10 ? 'bar' : 'bar';
                
                // إنشاء مصفوفة ألوان
                const backgroundColors = [];
                const colorPalette = [chartColors.primary, chartColors.success, chartColors.info, 
                                     chartColors.warning, chartColors.danger, chartColors.secondary];
                
                for (let i = 0; i < data.parameters.length; i++) {
                    backgroundColors.push(colorPalette[i % colorPalette.length]);
                }
                
                this.charts.parameters = new Chart(ctx, {
                    type: chartType,
                    data: {
                        labels: data.parameters,
                        datasets: [{
                            label: data.metric_label,
                            data: data.values,
                            backgroundColor: backgroundColors,
                            borderColor: backgroundColors,
                            borderWidth: 1
                        }]
                    },
                    options: {
                        ...defaultChartOptions,
                        indexAxis: data.parameters.length > 5 ? 'y' : 'x'
                    }
                });
            })
            .catch(error => console.error('Error loading parameters chart:', error));
    }
    
    // تحديث نوع الرسم البياني
    updateChartType(chartId, newType) {
        let chart;
        
        switch(chartId) {
            case 'sampleTrendsChart':
                chart = this.charts.sampleTrends;
                break;
            case 'sampleStatusChart':
                chart = this.charts.sampleStatus;
                break;
            case 'conformityChart':
                chart = this.charts.conformity;
                break;
            case 'regionChart':
                chart = this.charts.region;
                break;
            case 'parametersChart':
                chart = this.charts.parameters;
                break;
        }
        
        if (chart) {
            const data = chart.data;
            const options = chart.options;
            const ctx = chart.ctx;
            
            chart.destroy();
            
            // إعادة إنشاء المخطط بالنوع الجديد
            const newChart = new Chart(ctx, {
                type: newType,
                data: data,
                options: newType === 'doughnut' || newType === 'pie' ? 
                    {...options, cutout: newType === 'doughnut' ? '50%' : 0} : options
            });
            
            // تحديث مرجع المخطط
            switch(chartId) {
                case 'sampleTrendsChart':
                    this.charts.sampleTrends = newChart;
                    break;
                case 'sampleStatusChart':
                    this.charts.sampleStatus = newChart;
                    break;
                case 'conformityChart':
                    this.charts.conformity = newChart;
                    break;
                case 'regionChart':
                    this.charts.region = newChart;
                    break;
                case 'parametersChart':
                    this.charts.parameters = newChart;
                    break;
            }
        }
    }
    
    // تحميل بيانات المخطط كملف CSV
    downloadChartData(chartId) {
        let endpoint = '';
        let filename = '';
        
        switch(chartId) {
            case 'SampleTrends':
                endpoint = `/dashboard/api/sample-trends?period=${this.currentPeriod}`;
                filename = 'sample_trends.csv';
                break;
            case 'SampleStatus':
                endpoint = `/dashboard/api/sample-status?period=${this.currentPeriod}`;
                filename = 'sample_status.csv';
                break;
            case 'Conformity':
                endpoint = `/dashboard/api/conformity-trends?period=${this.currentPeriod}`;
                filename = 'conformity_trends.csv';
                break;
            case 'Region':
                endpoint = `/dashboard/api/region-distribution?period=${this.currentPeriod}`;
                filename = 'region_distribution.csv';
                break;
            case 'Parameters':
                const category = document.getElementById('parameterCategory').value;
                const metric = document.getElementById('parameterMetric').value;
                const limit = document.getElementById('parameterLimit').value;
                endpoint = `/dashboard/api/parameter-analysis?period=${this.currentPeriod}&category=${category}&metric=${metric}&limit=${limit}`;
                filename = 'parameter_analysis.csv';
                break;
        }
        
        if (endpoint) {
            fetch(endpoint)
                .then(response => response.json())
                .then(data => {
                    let csvContent = 'data:text/csv;charset=utf-8,';
                    
                    // تحويل البيانات إلى تنسيق CSV
                    if (chartId === 'SampleTrends') {
                        csvContent += 'التاريخ,عدد العينات\n';
                        data.dates.forEach((date, i) => {
                            csvContent += `${date},${data.counts[i]}\n`;
                        });
                    } else if (chartId === 'SampleStatus') {
                        csvContent += 'الحالة,العدد\n';
                        data.labels.forEach((label, i) => {
                            csvContent += `${label},${data.counts[i]}\n`;
                        });
                    } else if (chartId === 'Conformity') {
                        csvContent += 'التاريخ,نسبة المطابقة\n';
                        data.dates.forEach((date, i) => {
                            csvContent += `${date},${data.rates[i]}\n`;
                        });
                    } else if (chartId === 'Region') {
                        csvContent += 'المنطقة,عدد العينات\n';
                        data.regions.forEach((region, i) => {
                            csvContent += `${region},${data.counts[i]}\n`;
                        });
                    } else if (chartId === 'Parameters') {
                        csvContent += `المعيار,${data.metric_label}\n`;
                        data.parameters.forEach((param, i) => {
                            csvContent += `${param},${data.values[i]}\n`;
                        });
                    }
                    
                    // إنشاء رابط تنزيل
                    const encodedUri = encodeURI(csvContent);
                    const link = document.createElement('a');
                    link.setAttribute('href', encodedUri);
                    link.setAttribute('download', filename);
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                })
                .catch(error => console.error(`Error downloading ${chartId} data:`, error));
        }
    }
}

// تهيئة المخططات عند تحميل الصفحة
document.addEventListener('DOMContentLoaded', function() {
    const dashboardCharts = new DashboardCharts();
    dashboardCharts.loadAllCharts();
});