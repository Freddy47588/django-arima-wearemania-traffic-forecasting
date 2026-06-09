(function () {
    function readJson(id, fallback) {
        const element = document.getElementById(id);
        if (!element) return fallback;

        try {
            const raw = element.textContent.trim();
            return raw ? JSON.parse(raw) : fallback;
        } catch (error) {
            console.warn(`Data JSON ${id} tidak valid:`, error);
            return fallback;
        }
    }

    function numberFormat(value) {
        return new Intl.NumberFormat('id-ID').format(Number(value || 0));
    }

    function buildUnifiedLabels(actualLabels, forecastLabels) {
        return Array.from(new Set([...(actualLabels || []), ...(forecastLabels || [])]));
    }

    function alignSeries(unifiedLabels, sourceLabels, sourceValues) {
        const map = new Map();
        (sourceLabels || []).forEach(function (label, index) {
            map.set(label, Number(sourceValues[index] || 0));
        });
        return unifiedLabels.map(function (label) {
            return map.has(label) ? map.get(label) : null;
        });
    }

    let trafficChartInstance = null;

    function isoDateToTime(label) {
        const date = new Date(`${label}T00:00:00`);
        return Number.isNaN(date.getTime()) ? 0 : date.getTime();
    }

    function filterTrafficLabels(labels, actualLabels, forecastLabels, range) {
        if (range === 'all') return labels;

        if (range === 'bridge') {
            const actualSlice = (actualLabels || []).slice(-7);
            const forecastSlice = (forecastLabels || []).slice(0, 7);
            return buildUnifiedLabels(actualSlice, forecastSlice);
        }

        const latestTime = labels.reduce(function (latest, label) {
            return Math.max(latest, isoDateToTime(label));
        }, 0);

        if (!latestTime) return labels;

        const windowMs = 29 * 24 * 60 * 60 * 1000;
        return labels.filter(function (label) {
            return isoDateToTime(label) >= latestTime - windowMs;
        });
    }

    function hasPositiveValues(values) {
        return (values || []).some(function (value) {
            return Number(value || 0) > 0;
        });
    }

    function showEmptyState(emptyState, isEmpty) {
        if (!emptyState) return;
        emptyState.classList.toggle('active', isEmpty);
    }

    function buildChartColors(count) {
        const colors = [
            '#0f4c81',
            '#f97316',
            '#16a34a',
            '#7c3aed',
            '#0891b2',
            '#e11d48',
        ];

        return Array.from({ length: count }, function (_, index) {
            return colors[index % colors.length];
        });
    }

    function getChartFont() {
        return 'Inter, Segoe UI, Roboto, Helvetica Neue, Noto Sans, sans-serif';
    }

    function renderHorizontalBarChart(config) {
        const canvas = document.getElementById(config.canvasId);
        const emptyState = document.getElementById(config.emptyId);

        if (!canvas) return;

        const labels = readJson(config.labelsId, []);
        const values = readJson(config.valuesId, []);
        const hasData = labels.length > 0 && hasPositiveValues(values) && typeof Chart !== 'undefined';

        showEmptyState(emptyState, !hasData);

        if (!hasData) return;

        new Chart(canvas, {
            type: 'bar',
            data: {
                labels,
                datasets: [
                    {
                        label: config.label,
                        data: values,
                        borderWidth: 0,
                        borderRadius: 10,
                        backgroundColor: config.color
                    }
                ]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                return `${config.label}: ${numberFormat(context.parsed.x)}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        beginAtZero: true,
                        ticks: {
                            callback: function (value) {
                                return numberFormat(value);
                            }
                        },
                        grid: {
                            color: 'rgba(148, 163, 184, 0.22)'
                        }
                    },
                    y: {
                        ticks: {
                            font: {
                                family: getChartFont(),
                                weight: '700',
                                size: 11
                            }
                        },
                        grid: {
                            display: false
                        }
                    }
                }
            }
        });
    }

    function renderCategoryShareChart() {
        const canvas = document.getElementById('categoryShareChart');
        const emptyState = document.getElementById('categoryShareChartEmpty');

        if (!canvas) return;

        const labels = readJson('category-share-labels', []);
        const values = readJson('category-share-values', []);
        const hasData = labels.length > 0 && hasPositiveValues(values) && typeof Chart !== 'undefined';

        showEmptyState(emptyState, !hasData);

        if (!hasData) return;

        new Chart(canvas, {
            type: 'doughnut',
            data: {
                labels,
                datasets: [
                    {
                        data: values,
                        backgroundColor: buildChartColors(labels.length),
                        borderColor: '#ffffff',
                        borderWidth: 3,
                        hoverOffset: 6
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '62%',
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            usePointStyle: true,
                            boxWidth: 8,
                            padding: 14,
                            font: {
                                family: getChartFont(),
                                weight: '700',
                                size: 11
                            }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                const total = context.dataset.data.reduce(function (sum, value) {
                                    return sum + Number(value || 0);
                                }, 0);
                                const value = Number(context.parsed || 0);
                                const percent = total ? Math.round((value / total) * 100) : 0;
                                return `${context.label}: ${numberFormat(value)} views (${percent}%)`;
                            }
                        }
                    }
                }
            }
        });
    }

    function renderSuggestedCharts() {
        renderHorizontalBarChart({
            canvasId: 'topActualChart',
            emptyId: 'topActualChartEmpty',
            labelsId: 'top-actual-labels',
            valuesId: 'top-actual-values',
            label: 'Traffic Aktual',
            color: 'rgba(15, 76, 129, 0.84)'
        });

        renderHorizontalBarChart({
            canvasId: 'topForecastChart',
            emptyId: 'topForecastChartEmpty',
            labelsId: 'top-forecast-labels',
            valuesId: 'top-forecast-values',
            label: 'Prediksi Traffic',
            color: 'rgba(249, 115, 22, 0.86)'
        });

        renderCategoryShareChart();
    }

    function generateInsight() {
        const target = document.getElementById('autoInsight');
        if (!target) return;

        const insight = readJson('balanced-insight', {});

        if (insight && insight.summary) {
            target.textContent = insight.summary;
            return;
        }

        if (!insight || (!insight.recentActualViews && !insight.forecastViews)) {
            target.textContent = 'Belum ada data yang cukup untuk membuat insight. Upload CSV lalu jalankan forecast terlebih dahulu.';
            return;
        }

        if (!insight.forecastViews) {
            target.textContent = 'Data aktual sudah tersedia. Jalankan Buat Prediksi agar dashboard bisa membandingkan arah traffic ke depan.';
            return;
        }

        target.textContent = `Prediksi ${insight.comparisonDays || 7} hari ke depan menunjukkan estimasi traffic sekitar ${numberFormat(insight.forecastViews)} views. Dibandingkan periode aktual terbaru yang seimbang, traffic diperkirakan ${String(insight.trendLabel || 'stabil').toLowerCase()}.`;
    }

    function renderTrafficChart(range) {
        const canvas = document.getElementById('trafficChart');
        const emptyState = document.getElementById('trafficChartEmpty');
        if (!canvas) return;

        const actualLabels = readJson('actual-labels', []);
        const actualViews = readJson('actual-views', []);
        const forecastLabels = readJson('forecast-labels', []);
        const forecastViews = readJson('forecast-views', []);
        const forecastLower = readJson('forecast-lower', []);
        const forecastUpper = readJson('forecast-upper', []);

        generateInsight();

        const hasData = actualLabels.length > 0 || forecastLabels.length > 0;
        if (!hasData || typeof Chart === 'undefined') {
            if (emptyState) emptyState.classList.add('active');
            return;
        }

        if (emptyState) emptyState.classList.remove('active');

        const unifiedLabels = buildUnifiedLabels(actualLabels, forecastLabels);
        const labels = filterTrafficLabels(unifiedLabels, actualLabels, forecastLabels, range || '30');
        const actualData = alignSeries(labels, actualLabels, actualViews);
        const forecastData = alignSeries(labels, forecastLabels, forecastViews);
        const lowerData = alignSeries(labels, forecastLabels, forecastLower);
        const upperData = alignSeries(labels, forecastLabels, forecastUpper);

        if (trafficChartInstance) {
            trafficChartInstance.destroy();
        }

        trafficChartInstance = new Chart(canvas, {
            type: 'line',
            data: {
                labels,
                datasets: [
                    {
                        label: 'Traffic Aktual',
                        data: actualData,
                        borderWidth: 3,
                        pointRadius: 2,
                        tension: 0.34,
                        spanGaps: true
                    },
                    {
                        label: 'Prediksi Traffic',
                        data: forecastData,
                        borderWidth: 3,
                        pointRadius: 3,
                        borderDash: [8, 7],
                        tension: 0.34,
                        spanGaps: true
                    },
                    {
                        label: 'Batas Bawah',
                        data: lowerData,
                        borderWidth: 1,
                        pointRadius: 0,
                        borderDash: [4, 6],
                        tension: 0.34,
                        spanGaps: true
                    },
                    {
                        label: 'Batas Atas',
                        data: upperData,
                        borderWidth: 1,
                        pointRadius: 0,
                        borderDash: [4, 6],
                        tension: 0.34,
                        spanGaps: true
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false
                },
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            usePointStyle: true,
                            boxWidth: 8,
                            font: {
                                family: 'Inter, Segoe UI, Roboto, Helvetica Neue, Noto Sans, sans-serif',
                                weight: '700'
                            }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                return `${context.dataset.label}: ${numberFormat(context.parsed.y)}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        ticks: {
                            maxRotation: 0,
                            autoSkip: true,
                            maxTicksLimit: 8
                        },
                        grid: {
                            display: false
                        }
                    },
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function (value) {
                                return numberFormat(value);
                            }
                        }
                    }
                }
            }
        });
    }

    function setupChartRangeToggle() {
        const toggle = document.querySelector('.chart-range-toggle');
        if (!toggle) return;

        toggle.addEventListener('click', function (event) {
            const button = event.target.closest('button[data-range]');
            if (!button) return;

            toggle.querySelectorAll('button[data-range]').forEach(function (item) {
                item.classList.toggle('active', item === button);
            });

            renderTrafficChart(button.dataset.range || '30');
        });
    }

    function setupPredictionTableToggle() {
        const button = document.getElementById('predictionTableToggle');
        if (!button) return;

        const panel = button.closest('.table-panel');
        if (!panel) return;

        const extraRows = panel.querySelectorAll('.extra-prediction-row');
        if (!extraRows.length) {
            button.style.display = 'none';
            return;
        }

        button.addEventListener('click', function () {
            const showAll = !panel.classList.contains('show-all');
            panel.classList.toggle('show-all', showAll);
            button.textContent = showAll ? 'Tampilkan 10 Data' : 'Lihat Semua';
        });
    }

    function setupForecastProgress() {
        const form = document.getElementById('forecastForm');
        const modal = document.getElementById('forecastModal');
        const text = document.getElementById('forecastProgressText');

        if (!form || !modal || !text) return;

        form.addEventListener('submit', function () {
            const submitButton = form.querySelector('button[type="submit"]');

            if (submitButton) {
                submitButton.disabled = true;
                submitButton.classList.add('loading');
                submitButton.textContent = 'Membuat prediksi...';
            }

            modal.classList.add('active');
            modal.setAttribute('aria-hidden', 'false');

            const forecastDaysInput = form.querySelector('[name="forecast_days"]');
            const forecastDays = forecastDaysInput ? Number(forecastDaysInput.value || 7) : 7;
            const steps = Array.from(modal.querySelectorAll('.process-steps li'));
            const labels = [
                `Membaca data historis untuk prediksi ${forecastDays} hari ke depan...`,
                'Membersihkan dan merapikan time series per kategori...',
                'Menjalankan ARIMA. Jika data terlalu tipis, sistem memakai moving average fallback...',
                'Menyimpan prediksi dan metadata forecast run...',
                'Menunggu server selesai lalu dashboard akan dimuat ulang...'
            ];
            let stepIndex = 0;

            function renderStep() {
                steps.forEach(function (step, index) {
                    step.classList.toggle('done', index < stepIndex);
                    step.classList.toggle('active', index === stepIndex);
                });

                text.textContent = labels[stepIndex] || labels[labels.length - 1];
            }

            renderStep();

            window.setInterval(function () {
                stepIndex = Math.min(stepIndex + 1, labels.length - 1);
                renderStep();
            }, 1200);
        });
    }

    function setupForecastDaysLabel() {
        const form = document.getElementById('forecastForm');
        if (!form) return;

        const input = form.querySelector('[name="forecast_days"]');
        const button = form.querySelector('button[type="submit"]');
        if (!input || !button) return;

        function updateButtonLabel() {
            const value = Math.min(Math.max(Number(input.value || 7), 1), 14);
            button.textContent = `⚡ Buat Prediksi ${value} Hari`;
        }

        input.addEventListener('input', updateButtonLabel);
        updateButtonLabel();
    }

    document.addEventListener('DOMContentLoaded', function () {
        renderTrafficChart('30');
        setupChartRangeToggle();
        renderSuggestedCharts();
        setupPredictionTableToggle();
        setupForecastDaysLabel();
        setupForecastProgress();
    });
})();
