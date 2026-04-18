/**
 * Test suite for CSV download functionality
 * Tests individual chart download and batch download features
 */

// Mock DOM elements and functions for testing
const mockDocument = {
    createElement: (tag) => ({
        tagName: tag.toUpperCase(),
        className: '',
        style: { cssText: '' },
        textContent: '',
        innerHTML: '',
        appendChild: () => {},
        removeChild: () => {}
    }),
    getElementById: (id) => ({
        addEventListener: () => {},
        style: { display: 'block' }
    }),
    body: { appendChild: () => {}, removeChild: () => {} }
};

const mockWindow = {
    currentStatisticalResponse: null,
    Blob: function(content, options) {
        this.content = content;
        this.options = options;
    },
    URL: {
        createObjectURL: (blob) => 'mock-url'
    }
};

// Mock functions
function escapeCsvField(field) {
    if (field === null || field === undefined) return '';
    const stringField = String(field);
    if (stringField.includes(',') || stringField.includes('"') || stringField.includes('\n')) {
        return `"${stringField.replace(/"/g, '""')}"`;
    }
    return stringField;
}

function downloadCsv(data, filename) {
    const csvContent = data.join('\n');
    const blob = new mockWindow.Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = mockDocument.createElement('a');
    const url = mockWindow.URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', filename);
    link.style.visibility = 'hidden';
    mockDocument.body.appendChild(link);
    link.click();
    mockDocument.body.removeChild(link);
}

function downloadIndividualChartCsv(target, stats, analysis, targetIndex) {
    if (!stats || !stats.labels || !stats.datasets) {
        console.error('No data available for this chart');
        return;
    }

    let csvData = [];
    const labels = stats.labels;
    const datasets = stats.datasets;
    const chartTitle = target.legendFormat || target.expr || `Chart-${targetIndex + 1}`;
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);

    // Add headers
    const headerRow = ['Time', 'Relative Time (%)'];
    datasets.forEach(dataset => {
        headerRow.push(`${dataset.label} - Mean`);
        headerRow.push(`${dataset.label} - Std Dev`);
        headerRow.push(`${dataset.label} - Upper Bound`);
        headerRow.push(`${dataset.label} - Lower Bound`);
    });
    csvData.push(headerRow.map(escapeCsvField).join(','));

    // Add data rows
    labels.forEach((label, index) => {
        const row = [label, (index / (labels.length - 1) * 100).toFixed(2)];
        datasets.forEach(dataset => {
            row.push(dataset.data[index] || '');
            row.push(dataset.std_data ? dataset.std_data[index] : '');
            row.push(dataset.upper_data ? dataset.upper_data[index] : '');
            row.push(dataset.lower_data ? dataset.lower_data[index] : '');
        });
        csvData.push(row.map(escapeCsvField).join(','));
    });

    const filename = `statistical-analysis-${chartTitle.replace(/[^a-zA-Z0-9]/g, '-')}-${timestamp}.csv`;
    downloadCsv(csvData, filename);
}

function downloadAllChartsCsv() {
    const response = mockWindow.currentStatisticalResponse;
    if (!response || !response.panels) {
        console.error('No statistical data available for download');
        return;
    }

    let allCsvData = [];
    let headersAdded = false;

    response.panels.forEach(panel => {
        if (!panel.chart_data || !panel.chart_data.labels || !panel.chart_data.datasets) {
            return;
        }

        const labels = panel.chart_data.labels;
        const datasets = panel.chart_data.datasets;

        if (!headersAdded) {
            // Add headers
            const headerRow = ['Time', 'Relative Time (%)'];
            datasets.forEach(dataset => {
                headerRow.push(`${dataset.label} - Mean`);
                headerRow.push(`${dataset.label} - Std Dev`);
                headerRow.push(`${dataset.label} - Upper Bound`);
                headerRow.push(`${dataset.label} - Lower Bound`);
            });
            allCsvData.push(headerRow.map(escapeCsvField).join(','));
            headersAdded = true;
        }

        // Add data rows
        labels.forEach((label, index) => {
            const row = [label, (index / (labels.length - 1) * 100).toFixed(2)];
            datasets.forEach(dataset => {
                row.push(dataset.data[index] || '');
                row.push(dataset.std_data ? dataset.std_data[index] : '');
                row.push(dataset.upper_data ? dataset.upper_data[index] : '');
                row.push(dataset.lower_data ? dataset.lower_data[index] : '');
            });
            allCsvData.push(row.map(escapeCsvField).join(','));
        });
    });

    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
    downloadCsv(allCsvData, `statistical-analysis-all-${timestamp}.csv`);
}

// Test data
const mockStats = {
    labels: ['2024-01-01T00:00:00Z', '2024-01-01T01:00:00Z', '2024-01-01T02:00:00Z'],
    datasets: [{
        label: 'Test Metric',
        data: [100, 150, 120],
        std_data: [10, 15, 12],
        upper_data: [110, 165, 132],
        lower_data: [90, 135, 108]
    }]
};

const mockTarget = {
    expr: 'test_metric',
    legendFormat: 'Test Metric'
};

const mockAnalysis = {
    num_points: 100
};

const mockResponse = {
    panels: [{
        chart_data: mockStats,
        title: 'Test Panel'
    }]
};

// Test functions
function testIndividualDownload() {
    console.log('Testing individual chart download...');
    try {
        mockWindow.currentStatisticalResponse = mockResponse;
        downloadIndividualChartCsv(mockTarget, mockStats, mockAnalysis, 0);
        console.log('✅ Individual download test passed');
    } catch (error) {
        console.error('❌ Individual download test failed:', error);
    }
}

function testBatchDownload() {
    console.log('Testing batch download...');
    try {
        mockWindow.currentStatisticalResponse = mockResponse;
        downloadAllChartsCsv();
        console.log('✅ Batch download test passed');
    } catch (error) {
        console.error('❌ Batch download test failed:', error);
    }
}

function testCsvFieldEscaping() {
    console.log('Testing CSV field escaping...');
    const testCases = [
        { input: 'normal,text', expected: 'normal,text' },
        { input: 'text,with,commas', expected: '"text,with,commas"' },
        { input: 'text"with"quotes', expected: '"text""with""quotes"' },
        { input: 'text\nwith\nlines', expected: '"text\nwith\nlines"' },
        { input: null, expected: '' },
        { input: undefined, expected: '' }
    ];

    testCases.forEach((testCase, index) => {
        const result = escapeCsvField(testCase.input);
        if (result === testCase.expected) {
            console.log(`✅ Test case ${index + 1}: ${testCase.input} -> ${result}`);
        } else {
            console.error(`❌ Test case ${index + 1}: Expected "${testCase.expected}", got "${result}"`);
        }
    });
}

// Run tests
console.log('🧪 Running CSV Download Tests\n');
testCsvFieldEscaping();
console.log('\n');
testIndividualDownload();
console.log('\n');
testBatchDownload();
console.log('\n✅ All tests completed');
