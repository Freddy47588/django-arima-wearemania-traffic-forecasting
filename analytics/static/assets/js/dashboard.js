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

    function generateInsight(actualViews, forecastViews) {
        const target = document.getElementById('autoInsight');
        if (!target) return;

        const actualTotal = actualViews.reduce((total, value) => total + Number(value || 0), 0);
        const forecastTotal = forecastViews.reduce((total, value) => total + Number(value || 0), 0);

        if (!actualTotal && !forecastTotal) {
            target.textContent = 'Belum ada data yang cukup untuk membuat insight. Upload CSV lalu jalankan forecast terlebih dahulu.';
            return;
        }

        if (!forecastTotal) {
            target.textContent = `Data aktual sudah tersedia dengan total ${numberFormat(actualTotal)} views. Jalankan Generate Forecast agar dashboard bisa membandingkan arah traffic ke depan.`;
            return;
        }

        const delta = forecastTotal - actualTotal;
        const percent = actualTotal ? Math.round((delta / actualTotal) * 100) : 0;

        if (delta > 0) {
            target.textContent = `Forecast menunjukkan potensi kenaikan sekitar ${numberFormat(delta)} views (${percent}%) dibanding total aktual pada data yang sedang difilter. Prioritaskan kategori dengan estimasi tertinggi.`;
            return;
        }

        if (delta < 0) {
            target.textContent = `Forecast menunjukkan potensi penurunan sekitar ${numberFormat(Math.abs(delta))} views (${Math.abs(percent)}%). Redaksi bisa menyiapkan konten booster untuk menjaga traffic.`;
            return;
        }

        target.textContent = `Traffic aktual dan forecast terlihat relatif seimbang di angka ${numberFormat(actualTotal)} views. Pantau kategori teratas untuk menjaga konsistensi performa.`;
    }

    function renderTrafficChart() {
        const canvas = document.getElementById('trafficChart');
        const emptyState = document.getElementById('trafficChartEmpty');
        if (!canvas) return;

        const actualLabels = readJson('actual-labels', []);
        const actualViews = readJson('actual-views', []);
        const forecastLabels = readJson('forecast-labels', []);
        const forecastViews = readJson('forecast-views', []);
        const forecastLower = readJson('forecast-lower', []);
        const forecastUpper = readJson('forecast-upper', []);

        generateInsight(actualViews, forecastViews);

        const hasData = actualLabels.length > 0 || forecastLabels.length > 0;
        if (!hasData || typeof Chart === 'undefined') {
            if (emptyState) emptyState.classList.add('active');
            return;
        }

        if (emptyState) emptyState.classList.remove('active');

        const labels = buildUnifiedLabels(actualLabels, forecastLabels);
        const actualData = alignSeries(labels, actualLabels, actualViews);
        const forecastData = alignSeries(labels, forecastLabels, forecastViews);
        const lowerData = alignSeries(labels, forecastLabels, forecastLower);
        const upperData = alignSeries(labels, forecastLabels, forecastUpper);

        new Chart(canvas, {
            type: 'line',
            data: {
                labels,
                datasets: [
                    {
                        label: 'Actual Views',
                        data: actualData,
                        borderWidth: 3,
                        pointRadius: 2,
                        tension: 0.34,
                        spanGaps: true
                    },
                    {
                        label: 'Forecast Views',
                        data: forecastData,
                        borderWidth: 3,
                        pointRadius: 3,
                        borderDash: [8, 7],
                        tension: 0.34,
                        spanGaps: true
                    },
                    {
                        label: 'Lower Bound',
                        data: lowerData,
                        borderWidth: 1,
                        pointRadius: 0,
                        borderDash: [4, 6],
                        tension: 0.34,
                        spanGaps: true
                    },
                    {
                        label: 'Upper Bound',
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

    function setupForecastProgress() {
        const form = document.getElementById('forecastForm');
        const modal = document.getElementById('forecastModal');
        const bar = document.getElementById('forecastProgressBar');
        const text = document.getElementById('forecastProgressText');

        if (!form || !modal || !bar || !text) return;

        form.addEventListener('submit', function () {
            modal.classList.add('active');
            modal.setAttribute('aria-hidden', 'false');

            const forecastDaysInput = form.querySelector('[name="forecast_days"]');
            const forecastDays = forecastDaysInput ? Number(forecastDaysInput.value || 7) : 7;
            let progress = 0;
            const labels = [
                `Menyiapkan prediksi ${forecastDays} hari ke depan...`,
                'Membaca data historis...',
                'Menyusun time series...',
                'Menjalankan model ARIMA...',
                'Menyimpan hasil prediksi...'
            ];

            window.setInterval(function () {
                progress = Math.min(progress + Math.floor(Math.random() * 12) + 6, 94);
                const stepIndex = Math.min(Math.floor(progress / 25), labels.length - 1);
                bar.style.width = `${progress}%`;
                text.textContent = `${labels[stepIndex]} ${progress}%`;
            }, 450);
        });
    }

    document.addEventListener('DOMContentLoaded', function () {
        renderTrafficChart();
        setupForecastProgress();
    });
})();
