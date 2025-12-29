"""
Interactive web UI for reviewing and correcting sense clusters.

Usage:
    python scripts/cluster_review_ui.py

Then open http://localhost:5000 in your browser.
"""
import json
import logging
from pathlib import Path

import pandas as pd
from flask import Flask, jsonify, render_template_string, request

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Global data
clusters_df = None
current_word = None
corrections = {}


def load_clusters(filepath="data/04_feature/sense_clusters.parquet"):
    """Load sense clusters from parquet file."""
    global clusters_df
    clusters_df = pd.read_parquet(filepath)
    logger.info(f"Loaded {len(clusters_df)} cluster entries")
    return clusters_df


def get_unique_words():
    """Get list of all unique words in the dataset."""
    if clusters_df is None:
        return []
    return sorted(clusters_df['source_word'].unique().tolist())


def get_clusters_for_word(word):
    """Get all clusters for a specific word."""
    if clusters_df is None:
        return []

    word_data = clusters_df[clusters_df['source_word'] == word].copy()

    # Group by cluster ID
    clusters = []
    for cluster_id in sorted(word_data['sense_cluster_id'].unique()):
        cluster_examples = word_data[word_data['sense_cluster_id'] == cluster_id]

        clusters.append({
            'cluster_id': int(cluster_id),
            'size': len(cluster_examples),
            'examples': cluster_examples[['sentence_text', 'corpus_source']].to_dict('records'),
            'quality_score': cluster_examples['cluster_quality_score'].iloc[0] if 'cluster_quality_score' in cluster_examples.columns else None,
            'method': cluster_examples['clustering_method'].iloc[0] if 'clustering_method' in cluster_examples.columns else None,
        })

    return clusters


HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Sense Cluster Review</title>
    <meta charset="UTF-8">
    <style>
        * { box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        h1 { color: #333; margin-bottom: 10px; }
        .subtitle { color: #666; margin-bottom: 30px; }

        .controls {
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .word-selector { display: flex; gap: 10px; align-items: center; }
        .word-selector select {
            flex: 1;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 16px;
        }
        .word-selector button {
            padding: 10px 20px;
            background: #007bff;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
        }
        .word-selector button:hover { background: #0056b3; }

        .clusters-container {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }

        .cluster {
            background: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            position: relative;
        }
        .cluster.dragging { opacity: 0.5; }
        .cluster.drag-over {
            border: 2px dashed #007bff;
            background: #e7f3ff;
        }

        .cluster-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #eee;
        }
        .cluster-title {
            font-size: 18px;
            font-weight: bold;
            color: #333;
        }
        .cluster-info {
            font-size: 12px;
            color: #666;
        }
        .quality-badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: bold;
        }
        .quality-high { background: #d4edda; color: #155724; }
        .quality-medium { background: #fff3cd; color: #856404; }
        .quality-low { background: #f8d7da; color: #721c24; }

        .cluster-label {
            margin-bottom: 15px;
        }
        .cluster-label input {
            width: 100%;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
        }
        .cluster-label label {
            display: block;
            margin-bottom: 5px;
            font-size: 12px;
            color: #666;
            font-weight: 600;
        }

        .example {
            padding: 12px;
            margin-bottom: 8px;
            background: #f8f9fa;
            border-radius: 4px;
            cursor: move;
            border-left: 3px solid #007bff;
            transition: all 0.2s;
        }
        .example:hover {
            background: #e9ecef;
            transform: translateX(5px);
        }
        .example.dragging {
            opacity: 0.5;
            transform: rotate(2deg);
        }
        .example-text {
            font-size: 14px;
            line-height: 1.6;
            color: #333;
            margin-bottom: 5px;
        }
        .example-source {
            font-size: 11px;
            color: #999;
            text-transform: uppercase;
            font-weight: 600;
        }

        .add-cluster-btn {
            background: white;
            border: 2px dashed #007bff;
            color: #007bff;
            padding: 40px;
            text-align: center;
            border-radius: 8px;
            cursor: pointer;
            font-size: 16px;
            font-weight: bold;
            transition: all 0.2s;
        }
        .add-cluster-btn:hover {
            background: #e7f3ff;
            border-color: #0056b3;
            color: #0056b3;
        }

        .actions {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .actions button {
            padding: 12px 30px;
            border: none;
            border-radius: 4px;
            font-size: 16px;
            cursor: pointer;
            font-weight: 600;
        }
        .btn-save {
            background: #28a745;
            color: white;
        }
        .btn-save:hover { background: #218838; }
        .btn-reset {
            background: #6c757d;
            color: white;
        }
        .btn-reset:hover { background: #5a6268; }
        .btn-export {
            background: #17a2b8;
            color: white;
        }
        .btn-export:hover { background: #138496; }

        .message {
            padding: 15px;
            margin: 20px 0;
            border-radius: 4px;
            display: none;
        }
        .message.success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .message.error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📚 Sense Cluster Review Tool</h1>
        <p class="subtitle">Review and correct sense clustering results by dragging examples between clusters</p>

        <div class="controls">
            <div class="word-selector">
                <label for="word-select" style="font-weight: 600; min-width: 100px;">Select Word:</label>
                <select id="word-select">
                    <option value="">-- Choose a word --</option>
                </select>
                <button onclick="loadWord()">Load</button>
            </div>
        </div>

        <div id="message" class="message"></div>

        <div id="clusters-area">
            <p style="text-align: center; color: #999; padding: 40px;">Select a word to review its clusters</p>
        </div>

        <div class="actions" id="actions-bar" style="display: none;">
            <div>
                <span id="changes-count" style="color: #666; font-weight: 600;">No changes</span>
            </div>
            <div style="display: flex; gap: 10px;">
                <button class="btn-reset" onclick="resetChanges()">Reset</button>
                <button class="btn-export" onclick="exportCorrections()">Export JSON</button>
                <button class="btn-save" onclick="saveCorrections()">Save Changes</button>
            </div>
        </div>
    </div>

    <script>
        let currentWord = null;
        let clusters = [];
        let changes = new Map(); // example_text -> new_cluster_id
        let clusterLabels = new Map(); // cluster_id -> label
        let nextClusterId = 1000; // For new clusters

        // Load word list
        fetch('/api/words')
            .then(r => r.json())
            .then(words => {
                const select = document.getElementById('word-select');
                words.forEach(word => {
                    const option = document.createElement('option');
                    option.value = word;
                    option.textContent = word;
                    select.appendChild(option);
                });
            });

        function loadWord() {
            const word = document.getElementById('word-select').value;
            if (!word) return;

            currentWord = word;
            changes.clear();
            clusterLabels.clear();

            fetch(`/api/clusters/${word}`)
                .then(r => r.json())
                .then(data => {
                    clusters = data;
                    nextClusterId = Math.max(...clusters.map(c => c.cluster_id)) + 1;
                    renderClusters();
                    document.getElementById('actions-bar').style.display = 'flex';
                    updateChangesCount();
                });
        }

        function renderClusters() {
            const area = document.getElementById('clusters-area');
            area.innerHTML = '';

            const container = document.createElement('div');
            container.className = 'clusters-container';

            clusters.forEach(cluster => {
                container.appendChild(createClusterElement(cluster));
            });

            // Add "New Cluster" button
            const addBtn = document.createElement('div');
            addBtn.className = 'add-cluster-btn';
            addBtn.textContent = '+ Add New Cluster';
            addBtn.onclick = addNewCluster;
            container.appendChild(addBtn);

            area.appendChild(container);
        }

        function createClusterElement(cluster) {
            const div = document.createElement('div');
            div.className = 'cluster';
            div.dataset.clusterId = cluster.cluster_id;

            // Quality badge
            let qualityClass = 'quality-low';
            if (cluster.quality_score > 0.6) qualityClass = 'quality-high';
            else if (cluster.quality_score > 0.3) qualityClass = 'quality-medium';

            div.innerHTML = `
                <div class="cluster-header">
                    <div>
                        <div class="cluster-title">Cluster ${cluster.cluster_id}</div>
                        <div class="cluster-info">
                            ${cluster.size} examples
                            ${cluster.quality_score !== null ? `
                                <span class="quality-badge ${qualityClass}">
                                    Quality: ${(cluster.quality_score * 100).toFixed(0)}%
                                </span>
                            ` : ''}
                        </div>
                    </div>
                </div>
                <div class="cluster-label">
                    <label>Sense Label (optional):</label>
                    <input type="text"
                           placeholder="e.g., 'to pretend', 'to court', 'to intend'"
                           data-cluster-id="${cluster.cluster_id}"
                           oninput="updateClusterLabel(${cluster.cluster_id}, this.value)">
                </div>
                <div class="examples" id="cluster-${cluster.cluster_id}"></div>
            `;

            const examplesDiv = div.querySelector('.examples');
            cluster.examples.forEach((ex, idx) => {
                examplesDiv.appendChild(createExampleElement(ex, cluster.cluster_id));
            });

            // Drag and drop handlers
            div.addEventListener('dragover', handleDragOver);
            div.addEventListener('drop', handleDrop);
            div.addEventListener('dragleave', handleDragLeave);

            return div;
        }

        function createExampleElement(example, clusterId) {
            const div = document.createElement('div');
            div.className = 'example';
            div.draggable = true;
            div.dataset.sentence = example.sentence_text;
            div.dataset.originalCluster = clusterId;

            div.innerHTML = `
                <div class="example-text">${example.sentence_text}</div>
                <div class="example-source">${example.corpus_source}</div>
            `;

            div.addEventListener('dragstart', handleDragStart);
            div.addEventListener('dragend', handleDragEnd);

            return div;
        }

        function addNewCluster() {
            const newCluster = {
                cluster_id: nextClusterId++,
                size: 0,
                examples: [],
                quality_score: null,
                method: 'manual'
            };
            clusters.push(newCluster);
            renderClusters();
        }

        function updateClusterLabel(clusterId, label) {
            clusterLabels.set(clusterId, label);
            updateChangesCount();
        }

        let draggedElement = null;

        function handleDragStart(e) {
            draggedElement = e.target;
            e.target.classList.add('dragging');
            e.dataTransfer.effectAllowed = 'move';
        }

        function handleDragEnd(e) {
            e.target.classList.remove('dragging');
        }

        function handleDragOver(e) {
            if (e.preventDefault) {
                e.preventDefault();
            }
            e.dataTransfer.dropEffect = 'move';
            e.currentTarget.classList.add('drag-over');
            return false;
        }

        function handleDragLeave(e) {
            e.currentTarget.classList.remove('drag-over');
        }

        function handleDrop(e) {
            if (e.stopPropagation) {
                e.stopPropagation();
            }
            e.currentTarget.classList.remove('drag-over');

            if (!draggedElement) return false;

            const targetCluster = e.currentTarget;
            const targetClusterId = parseInt(targetCluster.dataset.clusterId);
            const sentence = draggedElement.dataset.sentence;
            const originalCluster = parseInt(draggedElement.dataset.originalCluster);

            if (targetClusterId !== originalCluster) {
                // Record the change
                changes.set(sentence, targetClusterId);

                // Move the element visually
                const examplesDiv = targetCluster.querySelector('.examples');
                examplesDiv.appendChild(draggedElement);

                updateChangesCount();
            }

            return false;
        }

        function updateChangesCount() {
            const count = changes.size + clusterLabels.size;
            const span = document.getElementById('changes-count');
            if (count === 0) {
                span.textContent = 'No changes';
                span.style.color = '#666';
            } else {
                span.textContent = `${count} change${count > 1 ? 's' : ''}`;
                span.style.color = '#007bff';
            }
        }

        function resetChanges() {
            if (!confirm('Reset all changes?')) return;
            changes.clear();
            clusterLabels.clear();
            loadWord();
        }

        function exportCorrections() {
            const corrections = {
                word: currentWord,
                changes: Object.fromEntries(changes),
                labels: Object.fromEntries(clusterLabels),
                timestamp: new Date().toISOString()
            };

            const blob = new Blob([JSON.stringify(corrections, null, 2)], {type: 'application/json'});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `corrections_${currentWord}_${Date.now()}.json`;
            a.click();
        }

        function saveCorrections() {
            const corrections = {
                word: currentWord,
                changes: Object.fromEntries(changes),
                labels: Object.fromEntries(clusterLabels)
            };

            fetch('/api/save', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(corrections)
            })
            .then(r => r.json())
            .then(result => {
                showMessage(result.message, 'success');
                changes.clear();
                clusterLabels.clear();
                updateChangesCount();
            })
            .catch(err => {
                showMessage('Error saving corrections: ' + err, 'error');
            });
        }

        function showMessage(text, type) {
            const msg = document.getElementById('message');
            msg.textContent = text;
            msg.className = `message ${type}`;
            msg.style.display = 'block';
            setTimeout(() => {
                msg.style.display = 'none';
            }, 3000);
        }
    </script>
</body>
</html>
"""


@app.route('/')
def index():
    """Serve the main UI."""
    return render_template_string(HTML_TEMPLATE)


@app.route('/api/words')
def api_words():
    """Get list of all words."""
    words = get_unique_words()
    return jsonify(words)


@app.route('/api/clusters/<word>')
def api_clusters(word):
    """Get clusters for a specific word."""
    clusters = get_clusters_for_word(word)
    return jsonify(clusters)


@app.route('/api/save', methods=['POST'])
def api_save():
    """Save corrections to a JSON file."""
    data = request.json
    word = data['word']
    changes = data['changes']
    labels = data['labels']

    # Save to corrections directory
    corrections_dir = Path('data/06_metrics/cluster_corrections')
    corrections_dir.mkdir(parents=True, exist_ok=True)

    correction_file = corrections_dir / f"{word}.json"

    # Load existing corrections if any
    if correction_file.exists():
        with open(correction_file, 'r', encoding='utf-8') as f:
            existing = json.load(f)
    else:
        existing = {}

    # Merge with new corrections
    if 'changes' not in existing:
        existing['changes'] = {}
    if 'labels' not in existing:
        existing['labels'] = {}

    existing['word'] = word
    existing['changes'].update(changes)
    existing['labels'].update(labels)
    existing['last_updated'] = pd.Timestamp.now().isoformat()

    # Save
    with open(correction_file, 'w', encoding='utf-8') as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)

    logger.info(f"Saved corrections for '{word}' to {correction_file}")

    return jsonify({
        'success': True,
        'message': f'Saved corrections for "{word}"'
    })


if __name__ == '__main__':
    # Load clusters on startup
    load_clusters()

    # Start server
    logger.info("Starting Cluster Review UI on http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
